"""Approval Lifecycle Service.

Manages persistent approval requests in PostgreSQL approval_requests table.
Supports idempotent approvals, prevents unauthorized execution, and blocks rejected actions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status

from app.core.events import EventChannel, EventType, default_event_manager
from app.models.policy import ApprovalDecisionRequest, ApprovalRequestRecord

logger = logging.getLogger("enterpriseai.approvals")


def _row_to_approval_record(row: tuple) -> ApprovalRequestRecord:
    (
        approval_id,
        action_id,
        decision_id,
        scenario_id,
        requested_at,
        required_domain,
        approval_status,
        decided_by,
        decided_at,
        reason,
    ) = row

    return ApprovalRequestRecord(
        approval_id=str(approval_id),
        action_id=str(action_id) if action_id else None,
        decision_id=str(decision_id) if decision_id else None,
        scenario_id=str(scenario_id) if scenario_id else None,
        requested_at=requested_at.isoformat() if requested_at else "",
        required_domain=str(required_domain) if required_domain else None,
        status=str(approval_status),
        decided_by=str(decided_by) if decided_by else None,
        decided_at=decided_at.isoformat() if decided_at else None,
        reason=str(reason) if reason else None,
    )


def create_approval_request(
    conn,
    required_domain: str,
    action_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> ApprovalRequestRecord:
    """Create a persistent approval request in PENDING status."""
    approval_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO approval_requests (
                approval_id, action_id, decision_id, scenario_id,
                requested_at, required_domain, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING
                approval_id, action_id, decision_id, scenario_id,
                requested_at, required_domain, status, decided_by,
                decided_at, reason;
            """,
            (
                str(approval_id),
                action_id,
                decision_id,
                scenario_id,
                now,
                required_domain.upper(),
            ),
        )
        row = cur.fetchone()
        conn.commit()

        default_event_manager.publish(
            event_type=EventType.APPROVAL_REQUESTED.value,
            channel=EventChannel.APPROVALS.value,
            entity_id=str(approval_id),
            entity_type="APPROVAL",
            scenario_id=str(scenario_id) if scenario_id else None,
            payload={
                "approval_id": str(approval_id),
                "action_id": str(action_id) if action_id else None,
                "decision_id": str(decision_id) if decision_id else None,
                "scenario_id": str(scenario_id) if scenario_id else None,
                "required_domain": required_domain.upper(),
                "status": "PENDING",
                "requested_at": now.isoformat(),
            },
        )

        return _row_to_approval_record(row)


def decide_approval_request(
    conn,
    approval_id: str,
    req: ApprovalDecisionRequest,
) -> ApprovalRequestRecord:
    """Authorize or reject an approval request idempotently."""
    try:
        val_uuid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid approval_id UUID: '{approval_id}'",
        )

    target_status = req.status.upper().strip()
    if target_status not in {"APPROVED", "REJECTED"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decision status must be 'APPROVED' or 'REJECTED', got '{req.status}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                approval_id, action_id, decision_id, scenario_id,
                requested_at, required_domain, status, decided_by,
                decided_at, reason
            FROM approval_requests
            WHERE approval_id = %s
            FOR UPDATE;
            """,
            (str(val_uuid),),
        )
        current = cur.fetchone()
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request '{approval_id}' not found.",
            )

        curr_status = current[6]
        # Idempotent response if already decided identically
        if curr_status == target_status:
            return _row_to_approval_record(current)

        if curr_status in {"APPROVED", "REJECTED"} and curr_status != target_status:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approval request '{approval_id}' already decided as '{curr_status}'.",
            )

        now = datetime.now(timezone.utc)
        cur.execute(
            """
            UPDATE approval_requests
            SET
                status = %s,
                decided_by = %s,
                decided_at = %s,
                reason = %s
            WHERE approval_id = %s
            RETURNING
                approval_id, action_id, decision_id, scenario_id,
                requested_at, required_domain, status, decided_by,
                decided_at, reason;
            """,
            (
                target_status,
                req.decided_by.strip(),
                now,
                req.reason,
                str(val_uuid),
            ),
        )
        updated = cur.fetchone()

        # If linked to an action in action_queue, advance action status
        action_id = current[1]
        if action_id:
            action_status = "APPROVED" if target_status == "APPROVED" else "REJECTED"
            cur.execute(
                """
                UPDATE action_queue
                SET status = %s, approved_by = %s
                WHERE action_id = %s;
                """,
                (action_status, req.decided_by.strip(), str(action_id)),
            )

        conn.commit()

        default_event_manager.publish(
            event_type=EventType.APPROVAL_DECIDED.value,
            channel=EventChannel.APPROVALS.value,
            entity_id=str(val_uuid),
            entity_type="APPROVAL",
            scenario_id=str(current[3]) if current[3] else None,
            payload={
                "approval_id": str(val_uuid),
                "action_id": str(current[1]) if current[1] else None,
                "status": target_status,
                "decided_by": req.decided_by.strip(),
                "decided_at": now.isoformat(),
                "reason": req.reason,
            },
        )

        return _row_to_approval_record(updated)


def get_approval(conn, approval_id: str) -> Optional[ApprovalRequestRecord]:
    """Retrieve approval request details by UUID."""
    try:
        val_uuid = uuid.UUID(approval_id)
    except ValueError:
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                approval_id, action_id, decision_id, scenario_id,
                requested_at, required_domain, status, decided_by,
                decided_at, reason
            FROM approval_requests
            WHERE approval_id = %s;
            """,
            (str(val_uuid),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return _row_to_approval_record(row)


def list_approvals(
    conn,
    status_filter: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ApprovalRequestRecord], int]:
    """List persistent approval requests with filtering and pagination."""
    clauses: list[str] = []
    params: list = []

    if status_filter:
        clauses.append("status = %s")
        params.append(status_filter.upper().strip())

    if domain:
        clauses.append("required_domain = %s")
        params.append(domain.upper().strip())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            approval_id, action_id, decision_id, scenario_id,
            requested_at, required_domain, status, decided_by,
            decided_at, reason,
            COUNT(*) OVER() AS total_count
        FROM approval_requests
        {where_sql}
        ORDER BY requested_at DESC, approval_id DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        return [], 0

    total = rows[0][10]
    records = [_row_to_approval_record(r[:10]) for r in rows]
    return records, total
