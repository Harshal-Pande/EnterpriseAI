"""Action Queue Management API endpoints.

Provides:
- POST /api/actions/propose : Propose a supply-chain action with policy gating
- GET /api/actions/ : List queued and executed actions with filtering
- GET /api/actions/{action_id} : Retrieve action details and execution history
- POST /api/actions/{action_id}/execute : Execute an action through execution gates
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.models.action import (
    ActionDetailResponse,
    ActionProposeRequest,
    ActionRecord,
)
from app.services.action_service import (
    execute_action,
    get_action,
    list_actions,
    propose_action,
)

logger = logging.getLogger("enterpriseai.api.actions")

router = APIRouter()


@router.post("/propose", response_model=ActionRecord, status_code=status.HTTP_201_CREATED)
def propose_new_action(
    req: ActionProposeRequest,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Propose a supply-chain action, evaluate policy, and queue for execution or approval."""
    if req.payload is None:
        req.payload = {}
    req.payload["proposed_by"] = current_user.user_id
    return propose_action(conn, req)


@router.get("/", response_model=List[ActionRecord])
def get_actions(
    scenario_id: Optional[str] = Query(None, description="Filter by workflow scenario UUID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PROPOSED, APPROVED, SUCCEEDED, FAILED)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db),
):
    """List actions from action_queue with filtering and deterministic pagination."""
    records, _ = list_actions(conn, scenario_id=scenario_id, status_filter=status_filter, limit=limit, offset=offset)
    return records


@router.get("/{action_id}", response_model=ActionDetailResponse)
def get_action_detail(action_id: str, conn=Depends(get_db)):
    """Retrieve detailed action record and execution history by UUID."""
    record = get_action(conn, action_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{action_id}' not found.",
        )
    return record


@router.post("/{action_id}/execute", response_model=ActionRecord)
def execute_queued_action(
    action_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Execute an action after re-evaluating policy gates, approvals, and preconditions."""
    return execute_action(conn, action_id, caller_id=current_user.user_id)
