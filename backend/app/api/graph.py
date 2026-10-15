"""Knowledge Graph API Router (Phase 8).

Exposes REST endpoints for:
- Operational graph health and engine status (/api/graph/status)
- Entity relationship queries and neighborhood exploration (/api/graph)
- Multi-hop supply chain disruption impact analysis (/api/graph/impact)
- Idempotent PostgreSQL to graph synchronization (/api/graph/sync)
- Provenance and dependency traversal (/api/graph/provenance/{entity_id})
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_role, UserRole
from app.db.database import get_db
from app.models.graph import (
    DisruptionImpactRequest,
    DisruptionImpactResponse,
    GraphStatusResponse,
    GraphSyncResponse,
    KnowledgeGraphResponse,
)
from app.services.graph_service import default_graph_service

logger = logging.getLogger("enterpriseai.api.graph")

router = APIRouter()


@router.get("/status", response_model=GraphStatusResponse)
def get_graph_status(conn=Depends(get_db)):
    """Retrieve operational status, connected engine, and graph metrics."""
    try:
        return default_graph_service.get_status(conn)
    except Exception as exc:
        logger.error("Error retrieving graph status: %s", exc)
        return GraphStatusResponse(
            status="DEGRADED",
            engine="RelationalGraphEngine",
            connected=False,
            error_message=str(exc)[:150],
        )


@router.get("", response_model=KnowledgeGraphResponse)
@router.get("/", response_model=KnowledgeGraphResponse)
def get_knowledge_graph(
    type: Optional[str] = Query(None, description="Filter by node entity type (Customer, Order, Product, Warehouse, Supplier)"),
    q: Optional[str] = Query(None, description="Search query across entity IDs, labels, or properties"),
    limit: int = Query(100, ge=5, le=500, description="Maximum nodes to return"),
    conn=Depends(get_db),
):
    """Query knowledge graph nodes and operational relationships with search and type filters."""
    try:
        return default_graph_service.get_graph(
            conn=conn,
            filter_type=type,
            query_text=q,
            max_nodes=limit,
        )
    except Exception as exc:
        logger.error("Error querying knowledge graph: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query knowledge graph: {str(exc)[:150]}",
        ) from exc


@router.post("/impact", response_model=DisruptionImpactResponse)
def analyze_disruption_impact(
    req: DisruptionImpactRequest,
    conn=Depends(get_db),
):
    """Perform multi-hop traversal to evaluate downstream supply chain disruption impact and recommend mitigations."""
    try:
        return default_graph_service.trace_impact(conn, req)
    except Exception as exc:
        logger.error("Error analyzing disruption impact: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disruption impact analysis failed: {str(exc)[:150]}",
        ) from exc


@router.post("/sync", response_model=GraphSyncResponse, dependencies=[Depends(require_role(UserRole.OPERATOR))])
def sync_knowledge_graph(conn=Depends(get_db)):
    """Idempotently ingest and synchronize supply chain domain entities from PostgreSQL into the Knowledge Graph."""
    try:
        return default_graph_service.sync_from_postgresql(conn)
    except Exception as exc:
        logger.error("Error synchronizing knowledge graph: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge graph synchronization failed: {str(exc)[:150]}",
        ) from exc


@router.get("/provenance/{entity_id}", response_model=KnowledgeGraphResponse)
def get_entity_provenance(
    entity_id: str,
    depth: int = Query(2, ge=1, le=4, description="Maximum traversal depth"),
    conn=Depends(get_db),
):
    """Retrieve the multi-hop dependency neighborhood and provenance path for a specific entity."""
    try:
        return default_graph_service.get_provenance(entity_id=entity_id, depth=depth, conn=conn)
    except Exception as exc:
        logger.error("Error retrieving provenance for %s: %s", entity_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve provenance: {str(exc)[:150]}",
        ) from exc
