"""Workflow API endpoints backed by PostgreSQL.

Provides:
- POST /api/workflow/ : Create persistent workflow instance (optionally executes agents)
- GET /api/workflow/ : List workflow instances with filtering and deterministic pagination
- GET /api/workflow/{workflow_id} : Retrieve workflow instance details by UUID (with backwards compatibility)
- POST /api/workflow/{workflow_id}/transition : Explicit validated state transition
- POST /api/workflow/{workflow_id}/execute : Execute specialist agents for an existing workflow
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import get_db
from app.models.workflow import (
    WorkflowCreateRequest,
    WorkflowInstance,
    WorkflowListResponse,
    WorkflowTransitionRequest,
)
from app.orchestration.graph import WorkflowGraph
from app.services.workflow_service import (
    create_workflow,
    get_workflow,
    list_workflows,
    transition_workflow_status,
)

logger = logging.getLogger("enterpriseai.api.workflow")

router = APIRouter()


@router.post("/", response_model=WorkflowInstance, status_code=status.HTTP_201_CREATED)
def start_new_workflow(
    req: WorkflowCreateRequest,
    conn=Depends(get_db),
):
    """Create a persistent workflow instance in PostgreSQL and optionally execute immediately."""
    instance = create_workflow(conn, req)

    if req.execute_immediately:
        graph = WorkflowGraph()
        initial_state = {
            "workflow_id": instance.workflow_id,
            "scenario_id": instance.scenario_id,
            "order_id": instance.linked_order_id or "ORD-UNKNOWN",
            "current_agent": "SupervisorAgent",
            "status": "queued",
            "audit_trail": [],
        }
        graph.run_workflow(initial_state, conn=conn)
        updated = get_workflow(conn, instance.workflow_id)
        if updated:
            return updated

    return instance


@router.get("/", response_model=WorkflowListResponse)
def get_workflows_list(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by workflow status"),
    template_id: Optional[str] = Query(None, description="Filter by scenario template ID"),
    order_id: Optional[str] = Query(None, description="Filter by linked order ID"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    conn=Depends(get_db),
):
    """List persistent workflow instances with deterministic pagination and ordering."""
    items, total = list_workflows(
        conn,
        status_filter=status_filter,
        template_id=template_id,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )
    return WorkflowListResponse(total=total, items=items, limit=limit, offset=offset)


@router.get("/{workflow_id}")
def get_workflow_status(workflow_id: str, conn=Depends(get_db)):
    """Retrieve persistent workflow details by UUID, or return legacy demo compatibility response."""
    # Preserved backward compatibility for starter demo fixtures
    if workflow_id in {"status", "wf-101"}:
        return {
            "workflow_id": workflow_id,
            "status": "active",
            "current_agent": "InventoryAgent",
            "scenario_id": workflow_id,
            "scenario_template_id": "TPL-010",
        }

    instance = get_workflow(conn, workflow_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow instance '{workflow_id}' not found.",
        )
    return instance


@router.post("/{workflow_id}/transition", response_model=WorkflowInstance)
def transition_workflow(
    workflow_id: str,
    req: WorkflowTransitionRequest,
    conn=Depends(get_db),
):
    """Explicitly transition a persistent workflow to a new status with validation."""
    return transition_workflow_status(conn, workflow_id, req)


@router.post("/{workflow_id}/execute", response_model=WorkflowInstance)
def execute_workflow(
    workflow_id: str,
    conn=Depends(get_db),
):
    """Execute specialist agents for an existing workflow instance."""
    instance = get_workflow(conn, workflow_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow instance '{workflow_id}' not found.",
        )

    graph = WorkflowGraph()
    initial_state = {
        "workflow_id": instance.workflow_id,
        "scenario_id": instance.scenario_id,
        "order_id": instance.linked_order_id or "ORD-UNKNOWN",
        "current_agent": "SupervisorAgent",
        "status": instance.status.lower(),
        "audit_trail": [],
    }
    graph.run_workflow(initial_state, conn=conn)

    updated = get_workflow(conn, workflow_id)
    return updated or instance
