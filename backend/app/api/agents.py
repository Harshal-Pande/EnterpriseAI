"""Specialist Agent API endpoints backed by PostgreSQL.

Provides:
- GET /api/agents/ : Summary of agent status (preserves backward compatibility)
- GET /api/agents/runs : List persistent agent execution records with filtering and pagination
- GET /api/agents/runs/{run_id} : Get single agent run detail by UUID
- POST /api/agents/runs : Start a persistent agent run linked to a workflow
- POST /api/agents/runs/{run_id}/complete : Complete an agent run with output payload
- POST /api/agents/runs/{run_id}/fail : Mark an agent run as failed with sanitized error
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import get_db
from app.models.agent_run import (
    AgentRunComplete,
    AgentRunCreate,
    AgentRunFail,
    AgentRunListResponse,
    AgentRunRecord,
)
from app.services.agent_run_service import (
    complete_agent_run,
    fail_agent_run,
    get_agent_run,
    list_agent_runs,
    start_agent_run,
)

logger = logging.getLogger("enterpriseai.api.agents")

router = APIRouter()


@router.get("/")
def get_agents_status():
    """Summary of agent statuses. Preserves backward compatibility with demo dashboard."""
    return {
        "supervisor": "idle",
        "inventory": "active",
        "procurement": "idle",
        "finance": "idle",
        "logistics": "idle",
    }


@router.get("/runs", response_model=AgentRunListResponse)
def get_agent_runs_list(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow run or scenario ID"),
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, RUNNING, COMPLETED, FAILED)"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    conn=Depends(get_db),
):
    """List persistent specialist-agent execution records with deterministic pagination."""
    effective_workflow = scenario_id or workflow_id
    items, total = list_agent_runs(
        conn,
        scenario_id=effective_workflow,
        agent_name=agent_name,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return AgentRunListResponse(total=total, items=items, limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=AgentRunRecord)
def get_agent_run_detail(run_id: str, conn=Depends(get_db)):
    """Retrieve detailed execution record for a single specialist agent run."""
    record = get_agent_run(conn, run_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent run '{run_id}' not found.",
        )
    return record


@router.post("/runs", response_model=AgentRunRecord, status_code=status.HTTP_201_CREATED)
def create_agent_run(
    req: AgentRunCreate,
    conn=Depends(get_db),
):
    """Start and persist a new specialist-agent run record linked to a workflow."""
    return start_agent_run(conn, req)


@router.post("/runs/{run_id}/complete", response_model=AgentRunRecord)
def mark_agent_run_complete(
    run_id: str,
    req: AgentRunComplete,
    conn=Depends(get_db),
):
    """Mark an existing specialist-agent run as COMPLETED with structured output."""
    return complete_agent_run(conn, run_id, req)


@router.post("/runs/{run_id}/fail", response_model=AgentRunRecord)
def mark_agent_run_failed(
    run_id: str,
    req: AgentRunFail,
    conn=Depends(get_db),
):
    """Mark an existing specialist-agent run as FAILED with sanitized error."""
    return fail_agent_run(conn, run_id, req)
