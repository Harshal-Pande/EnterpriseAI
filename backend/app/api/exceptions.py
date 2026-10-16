"""Operational Exceptions and Resolution Lifecycle API.

Endpoints:
- GET /api/exceptions/ : List operational exceptions with status, severity, and order filters
- GET /api/exceptions/{exception_id} : Detailed case file for an operational exception
- POST /api/exceptions/{exception_id}/propose-action : Propose an operational action to resolve the exception
- POST /api/exceptions/{exception_id}/approve : Authorize or reject a pending approval request linked to the exception
- POST /api/exceptions/{exception_id}/execute : Execute the approved action and resolve the exception
- POST /api/exceptions/{exception_id}/resume : Resolve exception and return order to processing queue
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.models.exception import (
    ExceptionActionProposeRequest,
    ExceptionApprovalRequest,
    ExceptionResolutionResponse,
    ExceptionResumeRequest,
    OperationalException,
    OperationalExceptionSummary,
)
from app.services.exception_service import (
    decide_exception_approval,
    execute_exception_action,
    get_exception_detail,
    list_exceptions,
    propose_action_for_exception,
    resume_order_from_exception,
)

logger = logging.getLogger("enterpriseai.api.exceptions")

router = APIRouter()


@router.get("/", response_model=List[OperationalExceptionSummary])
def get_exceptions(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (OPEN, AWAITING_APPROVAL, PROPOSED, APPROVED, RESOLVED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    order_id: Optional[str] = Query(None, description="Filter by linked order_id"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db),
):
    """Retrieve operational exceptions with linked order and entity metadata."""
    return list_exceptions(
        conn,
        status_filter=status_filter,
        severity=severity,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{exception_id}", response_model=OperationalException)
def get_exception(
    exception_id: str,
    conn=Depends(get_db),
):
    """Retrieve full case file for an operational exception including orders and actions."""
    return get_exception_detail(conn, exception_id)


@router.post("/{exception_id}/propose-action", response_model=Dict[str, Any])
def propose_action(
    exception_id: str,
    req: ExceptionActionProposeRequest,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Single-operator workspace: validate policy, enqueue action, and gate approval."""
    return propose_action_for_exception(
        conn,
        exception_id=exception_id,
        req=req,
        actor_id=current_user.user_id,
    )


@router.post("/{exception_id}/approve", response_model=Dict[str, Any])
def approve_exception_action(
    exception_id: str,
    req: ExceptionApprovalRequest,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Approve or reject a pending approval request linked to an operational exception."""
    return decide_exception_approval(
        conn,
        exception_id=exception_id,
        decision=req.decision,
        justification=req.justification,
        current_user=current_user,
    )


@router.post("/{exception_id}/execute", response_model=ExceptionResolutionResponse)
def execute_exception(
    exception_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Execute the approved action, mark exception RESOLVED, and update linked order."""
    return execute_exception_action(
        conn,
        exception_id=exception_id,
        caller_id=current_user.user_id,
    )


@router.post("/{exception_id}/resume", response_model=ExceptionResolutionResponse)
def resume_order(
    exception_id: str,
    req: Optional[ExceptionResumeRequest] = None,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Manually resolve the exception and return the order to the queue in QUEUED status."""
    notes = req.notes if req else None
    return resume_order_from_exception(
        conn,
        exception_id=exception_id,
        notes=notes,
        actor_id=current_user.user_id,
    )
