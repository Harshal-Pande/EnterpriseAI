"""Unit and integration tests for Phase 8 Knowledge Graph.

Covers:
- Knowledge Graph Pydantic schemas and constraints
- RelationalGraphEngine node/edge extraction from PostgreSQL
- Multi-hop disruption impact traversal and revenue-at-risk calculations
- Alternative supplier discovery
- Provenance subgraph extraction
- KnowledgeGraphService dual-engine resilience and fallback
- REST API endpoints (/api/graph/status, /api/graph, /api/graph/impact, /api/graph/sync, /api/graph/provenance/{entity_id})
- Supervisor agent graph context enrichment
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.graph import (
    GraphNode,
    GraphEdge,
    KnowledgeGraphNode,
    KnowledgeGraphEdge,
    KnowledgeGraphResponse,
    DisruptionImpactRequest,
    DisruptionImpactResponse,
    GraphSyncResponse,
    GraphStatusResponse,
)
from app.services.graph_service import (
    RelationalGraphEngine,
    KnowledgeGraphService,
    graph_service,
)


@pytest.fixture(autouse=True)
def enable_development_mode(monkeypatch):
    """Ensure test suite runs in development mode with active credential registry."""
    monkeypatch.setenv("APP_ENVIRONMENT", "development")


@pytest.fixture
def client() -> TestClient:
    """TestClient for FastAPI application with authenticated development viewer credentials."""
    with TestClient(app, headers={"X-API-Key": "dev-viewer-key"}) as test_client:
        yield test_client


# ─────────────────────────────────────────────────────────
# 1. Pydantic Models & Constraints
# ─────────────────────────────────────────────────────────

def test_graph_node_schema_validation():
    """Verify GraphNode schema validation, defaults, and serializability."""
    node = GraphNode(
        id="sup-1",
        label="Apex Industrial Metals",
        type="Supplier",
        properties={"tier": 1, "country": "IN", "reliability": 0.94},
        status="Active",
        source_table="dim_supplier",
        source_id="1",
    )
    assert node.id == "sup-1"
    assert node.type == "Supplier"
    assert node.properties["tier"] == 1
    assert node.status == "Active"

    # Edge validation
    edge = GraphEdge(
        id="edge-sup1-prod1",
        source="sup-1",
        target="prod-1",
        type="SUPPLIES",
        label="SUPPLIES",
        properties={"unit_cost_inr": 450.0},
    )
    assert edge.source == "sup-1"
    assert edge.target == "prod-1"
    assert edge.directed is True


def test_disruption_impact_request_validation():
    """Verify DisruptionImpactRequest limits and defaults."""
    req = DisruptionImpactRequest(
        entity_type="Supplier",
        entity_id="sup-b",
        severity="HIGH",
        max_depth=3,
        simulate_alternatives=True,
    )
    assert req.entity_id == "sup-b"
    assert req.max_depth == 3

    # DisruptionImpactResponse validation
    resp = DisruptionImpactResponse(
        disruption_origin="sup-b",
        origin_type="Supplier",
        severity="HIGH",
        affected_order_ids=["ord-1042"],
        affected_product_ids=["prod-800"],
        affected_warehouse_ids=["wh-nagpur"],
        total_revenue_at_risk_inr=1250000.0,
        alternative_suppliers=[
            {"supplier_id": "sup-c", "name": "Tata Advanced", "unit_cost_inr": 475.0}
        ],
        traversal_paths=[["sup-b", "prod-800", "ord-1042"]],
        mitigation_recommendation="Reroute order ord-1042 to alternate supplier Tata Advanced",
        graph_engine="relational_graph_hybrid",
        analyzed_at="2026-10-15T02:00:00Z",
    )
    assert resp.total_revenue_at_risk_inr == 1250000.0
    assert len(resp.affected_order_ids) == 1


# ─────────────────────────────────────────────────────────
# 2. RelationalGraphEngine Traversal & Discovery
# ─────────────────────────────────────────────────────────

def test_relational_graph_engine_extract_graph():
    """Verify extraction of real or fallback nodes and edges from PostgreSQL."""
    nodes, edges = RelationalGraphEngine.extract_graph(None, max_nodes=100)
    assert len(nodes) > 0
    assert len(edges) > 0

    # Verify standard types exist
    node_types = {n.type for n in nodes}
    assert "Order" in node_types or "Product" in node_types or "Supplier" in node_types


def test_relational_graph_engine_downstream_impact():
    """Verify multi-hop impact analysis (Supplier -> Product -> Order)."""
    req = DisruptionImpactRequest(
        entity_type="Supplier",
        entity_id="sup-b",
        severity="HIGH",
        max_depth=4,
        simulate_alternatives=True,
    )
    impact = RelationalGraphEngine.analyze_disruption_impact(req)

    assert impact.disruption_origin == "sup-b"
    assert impact.origin_type == "Supplier"
    assert impact.severity == "HIGH"
    assert isinstance(impact.affected_order_ids, list)
    assert isinstance(impact.total_revenue_at_risk_inr, float)
    assert len(impact.mitigation_recommendation) > 0


def test_relational_graph_engine_provenance():
    """Verify entity provenance subgraph extraction up to bounded depth."""
    provenance = RelationalGraphEngine.get_provenance("ord-1042", depth=2)

    assert isinstance(provenance, KnowledgeGraphResponse)
    assert provenance.node_count >= 1
    node_ids = {n.id for n in provenance.nodes}
    assert "ord-1042" in node_ids


# ─────────────────────────────────────────────────────────
# 3. KnowledgeGraphService Resilience & Fallback
# ─────────────────────────────────────────────────────────

def test_service_status_offline_neo4j():
    """Verify KnowledgeGraphService reports status and falls back gracefully when Neo4j is offline."""
    service = KnowledgeGraphService()
    status = service.get_status()

    assert isinstance(status, GraphStatusResponse)
    assert status.status in ("HEALTHY", "DEGRADED", "OFFLINE")
    assert "RelationalGraphEngine" in status.engine or "Neo4j" in status.engine
    assert status.node_count >= 0
    assert status.relationship_count >= 0


def test_service_sync_knowledge_graph():
    """Verify sync_knowledge_graph persists/indexes records and returns statistics."""
    service = KnowledgeGraphService()
    sync_res = service.sync_knowledge_graph()

    assert isinstance(sync_res, GraphSyncResponse)
    assert sync_res.status == "SUCCESS"
    assert sync_res.synced_nodes > 0
    assert sync_res.duration_ms >= 0


# ─────────────────────────────────────────────────────────
# 4. REST API Endpoints
# ─────────────────────────────────────────────────────────

def test_api_graph_status(client: TestClient):
    """GET /api/graph/status returns operational status."""
    resp = client.get("/api/graph/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "engine" in data
    assert "node_count" in data
    assert "relationship_count" in data


def test_api_get_graph(client: TestClient):
    """GET /api/graph returns nodes and edges with limit filter."""
    resp = client.get("/api/graph?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "node_count" in data
    assert "edge_count" in data
    assert len(data["nodes"]) <= 50


def test_api_get_graph_filtered_by_type(client: TestClient):
    """GET /api/graph?type=Product returns product entities."""
    resp = client.get("/api/graph?type=Product&limit=25")
    assert resp.status_code == 200
    data = resp.json()
    for node in data["nodes"]:
        assert node["type"] == "Product"


def test_api_disruption_impact(client: TestClient):
    """POST /api/graph/impact executes multi-hop analysis."""
    payload = {
        "entity_type": "Supplier",
        "entity_id": "sup-b",
        "severity": "HIGH",
        "max_depth": 3,
        "simulate_alternatives": True,
    }
    resp = client.post("/api/graph/impact", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["disruption_origin"] == "sup-b"
    assert "affected_order_ids" in data
    assert "total_revenue_at_risk_inr" in data
    assert "mitigation_recommendation" in data


def test_api_sync_graph_role_enforcement(client: TestClient):
    """POST /api/graph/sync enforces role hierarchy: VIEWER forbidden (403), OPERATOR allowed (200)."""
    # 1. Viewer attempt -> 403 Forbidden
    viewer_resp = client.post("/api/graph/sync", headers={"X-API-Key": "dev-viewer-key"})
    assert viewer_resp.status_code == 403

    # 2. Operator attempt -> 200 OK
    op_resp = client.post("/api/graph/sync", headers={"X-API-Key": "dev-operator-key"})
    assert op_resp.status_code == 200
    data = op_resp.json()
    assert data["status"] == "SUCCESS"
    assert data["synced_nodes"] > 0
    assert data["synced_edges"] > 0


def test_api_provenance(client: TestClient):
    """GET /api/graph/provenance/{entity_id} retrieves lineage subgraph."""
    resp = client.get("/api/graph/provenance/ord-1042?depth=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert any(n["id"] == "ord-1042" for n in data["nodes"])


# ─────────────────────────────────────────────────────────
# 5. Supervisor Agent Integration
# ─────────────────────────────────────────────────────────

def test_supervisor_agent_incorporates_graph_impact():
    """Verify SupervisorAgent queries the knowledge graph and grounds decisions."""
    from app.agents.supervisor import SupervisorAgent

    agent = SupervisorAgent()
    mock_order = {
        "order_id": "ORD-1042",
        "customer_id": "CUST-001",
        "product_id": "PROD-800",
        "status": "DELAYED",
        "delay_days": 4,
    }

    result = agent.run(mock_order)
    assert isinstance(result, dict)
    assert result["status"] == "DECISION_SYNTHESIZED"
    assert "decision_code" in result
    assert "recommended_action" in result
    assert "evidence_refs" in result
    assert isinstance(result["evidence_refs"], list)
