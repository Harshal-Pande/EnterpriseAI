"""Approval Management API endpoints.

Provides:
- GET /api/approvals/ : List pending and decided approval requests with filtering
- GET /api/approvals/{approval_id} : Retrieve approval request details by UUID
- POST /api/approvals/{approval_id}/decision : Authorize or reject an approval request idempotently
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.models.policy import ApprovalDecisionRequest, ApprovalRequestRecord
from app.services.action_service import get_action
from app.services.approval_service import (
    decide_approval_request,
    get_approval,
    list_approvals,
)

logger = logging.getLogger("enterpriseai.api.approvals")

router = APIRouter()


@router.get("/", response_model=List[ApprovalRequestRecord])
def get_approvals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, APPROVED, REJECTED)"),
    domain: Optional[str] = Query(None, description="Filter by required domain (FINANCE, QUALITY, etc.)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db),
):
    """List persistent approval requests with deterministic ordering."""
    records, _ = list_approvals(conn, status_filter=status_filter, domain=domain, limit=limit, offset=offset)
    return records


@router.get("/{approval_id}", response_model=ApprovalRequestRecord)
def get_approval_detail(approval_id: str, conn=Depends(get_db)):
    """Retrieve detailed approval request record by UUID."""
    record = get_approval(conn, approval_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found.",
        )
    return record


@router.post("/{approval_id}/decision", response_model=ApprovalRequestRecord)
def submit_approval_decision(
    approval_id: str,
    req: ApprovalDecisionRequest,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Authorize or reject an approval request idempotently with domain, amount, and self-approval enforcement."""
    approval_rec = get_approval(conn, approval_id)
    if not approval_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found.",
        )

    # 1. Domain permission check
    if approval_rec.required_domain and not current_user.can_approve_domain(approval_rec.required_domain):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.user_id}' with role '{current_user.role.value}' is not authorized to decide {approval_rec.required_domain} approvals.",
        )

    # 2. Enforce server-side actor identity (cannot be forged by client request body)
    req.decided_by = current_user.user_id

    # 3. Action-level checks: self-approval and threshold limits
    if approval_rec.action_id:
        action_detail = get_action(conn, approval_rec.action_id)
        if action_detail and action_detail.action:
            act = action_detail.action
            # Self-approval restriction
            proposer = act.payload.get("proposed_by") or act.payload.get("proposer_id")
            if proposer and proposer == current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Self-approval is prohibited: user '{current_user.user_id}' proposed this action.",
                )

            # Spending threshold limit check
            amount = float(act.payload.get("estimated_cost") or act.payload.get("amount") or act.payload.get("spend") or 0.0)
            if not current_user.can_approve_amount(amount):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Action amount (₹{amount:,.0f}) exceeds approval limit for role '{current_user.role.value}' (max ₹{current_user.max_approval_amount:,.0f}). Requires ADMIN role.",
                )

    return decide_approval_request(conn, approval_id, req)
