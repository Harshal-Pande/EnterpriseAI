"""Knowledge Graph Pydantic Models (Phase 8).

Defines strongly-typed data structures for:
- Nodes and Relationships in the supply chain knowledge graph
- Graph query and filter responses
- Disruption impact analysis requests and results
- Provenance and dependency traversal paths
- Ingestion and synchronization status
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class KnowledgeGraphNode(BaseModel):
    """A node in the enterprise knowledge graph representing a supply chain entity."""
    id: str = Field(..., description="Unique stable entity identifier")
    label: str = Field(..., description="Human-readable display label")
    type: str = Field(..., description="Node entity category (Customer, Order, Product, Warehouse, Supplier, etc.)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes and metadata")
    status: Optional[str] = Field(None, description="Operational status or state")
    source_table: Optional[str] = Field(None, description="Authoritative PostgreSQL source table")
    source_id: Optional[str] = Field(None, description="Authoritative primary key in PostgreSQL")


class KnowledgeGraphEdge(BaseModel):
    """A directed edge in the enterprise knowledge graph representing an operational relationship."""
    id: str = Field(..., description="Unique relationship identifier")
    source: str = Field(..., description="Source node identifier")
    target: str = Field(..., description="Target node identifier")
    type: str = Field(..., description="Relationship type (PLACED, REQUIRES, STORES, SUPPLIES, etc.)")
    label: Optional[str] = Field(None, description="Display label for edge")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship metadata")
    directed: bool = Field(True, description="True if relationship has direction")


class KnowledgeGraphResponse(BaseModel):
    """Payload returned by graph exploration queries."""
    nodes: List[KnowledgeGraphNode]
    edges: List[KnowledgeGraphEdge]
    node_count: int
    edge_count: int
    query_time_ms: float
    engine: str = Field("RelationalGraphEngine", description="Engine used (Neo4j / RelationalGraphEngine)")
    timestamp: str


class DisruptionImpactRequest(BaseModel):
    """Request to evaluate downstream supply chain impact from an incident or bottleneck."""
    entity_type: str = Field(..., description="Type of originating entity (Supplier, Warehouse, Product, LogisticsRoute)")
    entity_id: str = Field(..., description="Identifier of the affected entity (e.g., SUPP-001, WH-01)")
    severity: str = Field("MEDIUM", description="Disruption severity (LOW, MEDIUM, HIGH, CRITICAL)")
    max_depth: int = Field(3, ge=1, le=6, description="Maximum traversal hops for dependency tracing")
    simulate_alternatives: bool = Field(True, description="Whether to locate alternative suppliers or routes")


class TraversalHop(BaseModel):
    """A single link in a multi-hop impact path."""
    source_id: str
    source_type: str
    relationship: str
    target_id: str
    target_type: str


class DisruptionImpactResponse(BaseModel):
    """Multi-hop downstream impact analysis results."""
    disruption_origin: str
    origin_type: str
    severity: str
    affected_order_ids: List[str]
    affected_product_ids: List[str]
    affected_warehouse_ids: List[str]
    total_revenue_at_risk_inr: float
    alternative_suppliers: List[Dict[str, Any]] = Field(default_factory=list)
    traversal_paths: List[List[Any]] = Field(default_factory=list)
    mitigation_recommendation: str
    graph_engine: str
    analyzed_at: str


class GraphStatusResponse(BaseModel):
    """Operational status and connectivity metrics for the knowledge graph subsystem."""
    status: str = Field(..., description="HEALTHY, DEGRADED, or OFFLINE")
    engine: str = Field(..., description="Active engine: Neo4j or RelationalGraphEngine")
    connected: bool
    uri: Optional[str] = None
    node_count: int = 0
    relationship_count: int = 0
    available_labels: List[str] = Field(default_factory=list)
    available_relationship_types: List[str] = Field(default_factory=list)
    last_synced_at: Optional[str] = None
    error_message: Optional[str] = None


class GraphSyncResponse(BaseModel):
    """Response returned after synchronizing graph data from PostgreSQL."""
    status: str
    synced_nodes: int
    synced_edges: int
    duration_ms: float
    engine: str
    message: str


# Aliases for developer convenience and frontend parity
GraphNode = KnowledgeGraphNode
GraphEdge = KnowledgeGraphEdge

