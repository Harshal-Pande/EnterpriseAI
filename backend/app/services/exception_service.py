"""Operational Exception Service.

Manages unified operational exceptions and single-operator resolution lifecycle:
1. List unresolved and historical exceptions.
2. Full exception case file detail with order, scenario, policy, and action context.
3. Operator action proposal with deterministic policy gating.
4. Human-in-the-loop approval gating.
5. Action execution with before/after state simulation.
6. Order resumption in processing queue.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.events import EventChannel, EventType, default_event_manager
from app.core.security import AuthUser, UserRole
from app.models.action import ActionProposeRequest
from app.models.exception import (
    ExceptionActionProposeRequest,
    ExceptionResolutionResponse,
    OperationalException,
    OperationalExceptionSummary,
)
from app.models.policy import ApprovalDecisionRequest
from app.services.action_service import execute_action, get_action, propose_action
from app.services.approval_service import create_approval_request, decide_approval_request

logger = logging.getLogger("enterpriseai.exceptions")


def _log_exception_event(
    cur,
    event_type: str,
    status_val: str,
    exception_id: str,
    order_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    actor_id: str = "operator",
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    now = datetime.now(timezone.utc)
    data = payload or {}
    serialized = json.dumps(data, sort_keys=True, default=str)
    payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    cur.execute(
        """
        INSERT INTO event_log (
            event_id, event_timestamp, event_type, entity_type, entity_id,
            scenario_id, actor_type, actor_id, status, payload_hash, evidence_refs, source_channel
        ) VALUES (
            gen_random_uuid(), %s, %s, 'EXCEPTION', %s,
            %s, 'USER', %s, %s, %s, %s, 'EXCEPTION_WORKSPACE'
        );
        """,
        (
            now,
            event_type,
            exception_id,
            scenario_id,
            actor_id,
            status_val,
            payload_hash,
            serialized,
        ),
    )


def list_exceptions(
    conn,
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    order_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[OperationalExceptionSummary]:
    """Retrieve operational exceptions with linked order and entity metadata."""
    clauses: list[str] = []
    params: list = []

    if status_filter:
        clauses.append("e.status = %s")
        params.append(status_filter.upper().strip())

    if severity:
        clauses.append("e.severity = %s")
        params.append(severity.upper().strip())

    if order_id:
        clauses.append("e.order_id = %s")
        params.append(order_id.strip())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            e.exception_id,
            e.order_id,
            e.severity,
            e.exception_type,
            e.cause,
            e.owner_role,
            e.status,
            e.created_at,
            e.updated_at,
            e.resolved_at,
            o.customer_ref,
            o.entity_id
        FROM operational_exceptions e
        LEFT JOIN orders o ON e.order_id = o.order_id
        {where_sql}
        ORDER BY
            CASE WHEN e.status = 'OPEN' THEN 1
                 WHEN e.status = 'AWAITING_APPROVAL' THEN 2
                 WHEN e.status = 'PROPOSED' THEN 3
                 WHEN e.status = 'APPROVED' THEN 4
                 ELSE 5 END ASC,
            e.created_at DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    results: list[OperationalExceptionSummary] = []
    for r in rows:
        results.append(
            OperationalExceptionSummary(
                exception_id=str(r[0]),
                order_id=r[1],
                severity=r[2],
                exception_type=r[3],
                cause=r[4],
                owner_role=r[5],
                status=r[6],
                created_at=r[7].isoformat() if r[7] else "",
                updated_at=r[8].isoformat() if r[8] else "",
                resolved_at=r[9].isoformat() if r[9] else None,
                customer_ref=r[10],
                entity_id=r[11],
            )
        )
    return results


def get_exception_detail(conn, exception_id: str) -> OperationalException:
    """Retrieve full case file for an operational exception including orders and actions."""
    try:
        val_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exception_id UUID '{exception_id}'",
        )

    sql = """
        SELECT
            e.exception_id,
            e.order_id,
            e.scenario_id,
            e.workflow_run_id,
            e.decision_id,
            e.action_id,
            e.approval_id,
            e.severity,
            e.exception_type,
            e.cause,
            e.owner_role,
            e.status,
            e.ai_recommendation,
            e.proposed_action,
            e.resolution_notes,
            e.created_at,
            e.updated_at,
            e.resolved_at
        FROM operational_exceptions e
        WHERE e.exception_id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (str(val_uuid),))
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exception '{exception_id}' not found.",
            )

        order_id = row[1]
        action_id = row[5]
        approval_id = row[6]

        order_details: Optional[Dict[str, Any]] = None
        if order_id:
            cur.execute(
                """
                SELECT o.order_id, o.customer_ref, o.entity_id, o.status, o.priority, o.currency,
                       o.required_delivery_at,
                       COALESCE(SUM(ol.requested_qty * ol.unit_price_inr), 0) as total_amount_inr
                FROM orders o
                LEFT JOIN order_lines ol ON o.order_id = ol.order_id
                WHERE o.order_id = %s
                GROUP BY o.order_id, o.customer_ref, o.entity_id, o.status, o.priority, o.currency, o.required_delivery_at;
                """,
                (order_id,),
            )
            o_row = cur.fetchone()
            if o_row:
                order_details = {
                    "order_id": o_row[0],
                    "customer_ref": o_row[1],
                    "entity_id": o_row[2],
                    "status": o_row[3],
                    "priority": o_row[4],
                    "currency": o_row[5],
                    "required_delivery_at": o_row[6].isoformat() if o_row[6] else None,
                    "total_amount_inr": float(o_row[7]),
                }

        action_details: Optional[Dict[str, Any]] = None
        if action_id:
            cur.execute(
                """
                SELECT action_id, action_type, status, requires_approval, payload, result
                FROM action_queue WHERE action_id = %s;
                """,
                (str(action_id),),
            )
            a_row = cur.fetchone()
            if a_row:
                action_details = {
                    "action_id": str(a_row[0]),
                    "action_type": a_row[1],
                    "status": a_row[2],
                    "requires_approval": a_row[3],
                    "payload": a_row[4],
                    "result": a_row[5],
                }

        approval_details: Optional[Dict[str, Any]] = None
        if approval_id:
            cur.execute(
                """
                SELECT approval_id, required_domain, status, decided_by, decided_at, reason
                FROM approval_requests WHERE approval_id = %s;
                """,
                (str(approval_id),),
            )
            appr_row = cur.fetchone()
            if appr_row:
                approval_details = {
                    "approval_id": str(appr_row[0]),
                    "required_domain": appr_row[1],
                    "status": appr_row[2],
                    "decided_by": appr_row[3],
                    "decided_at": appr_row[4].isoformat() if appr_row[4] else None,
                    "reason": appr_row[5],
                }

    return OperationalException(
        exception_id=str(row[0]),
        order_id=row[1],
        scenario_id=str(row[2]) if row[2] else None,
        workflow_run_id=str(row[3]) if row[3] else None,
        decision_id=str(row[4]) if row[4] else None,
        action_id=str(row[5]) if row[5] else None,
        approval_id=str(row[6]) if row[6] else None,
        severity=row[7],
        exception_type=row[8],
        cause=row[9],
        owner_role=row[10],
        status=row[11],
        ai_recommendation=row[12] if isinstance(row[12], dict) else {},
        proposed_action=row[13] if isinstance(row[13], dict) else None,
        resolution_notes=row[14],
        created_at=row[15].isoformat() if row[15] else "",
        updated_at=row[16].isoformat() if row[16] else "",
        resolved_at=row[17].isoformat() if row[17] else None,
        order_details=order_details,
        action_details=action_details,
        approval_details=approval_details,
    )


def propose_action_for_exception(
    conn,
    exception_id: str,
    req: ExceptionActionProposeRequest,
    actor_id: str = "operator",
) -> Dict[str, Any]:
    """Single-operator workspace: validate policy, enqueue action, and gate approval."""
    try:
        val_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exception_id UUID '{exception_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT exception_id, order_id, scenario_id, status
            FROM operational_exceptions WHERE exception_id = %s;
            """,
            (str(val_uuid),),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exception '{exception_id}' not found.",
            )

        current_status = row[3]
        if current_status == "RESOLVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exception '{exception_id}' is already RESOLVED.",
            )

        order_id = row[1]
        scenario_id = str(row[2]) if row[2] else None

        if not scenario_id:
            if order_id:
                cur.execute(
                    "SELECT scenario_id FROM scenario_instances WHERE linked_order_id = %s LIMIT 1;",
                    (order_id,),
                )
                sc_row = cur.fetchone()
                if sc_row:
                    scenario_id = str(sc_row[0])
            if not scenario_id:
                sc_uuid = uuid.uuid4()
                now_sc = datetime.now(timezone.utc)
                cur.execute(
                    """
                    INSERT INTO scenario_instances (
                        scenario_id, scenario_template_id, scheduled_at, created_at,
                        status, severity, linked_order_id, idempotency_key
                    ) VALUES (
                        %s, 'TPL-001', %s, %s, 'INVESTIGATING', 'HIGH', %s, %s
                    );
                    """,
                    (str(sc_uuid), now_sc, now_sc, order_id, f"IDEMP-EXC-SCENARIO-{str(sc_uuid)[:8]}"),
                )
                scenario_id = str(sc_uuid)
            cur.execute(
                "UPDATE operational_exceptions SET scenario_id = %s WHERE exception_id = %s;",
                (scenario_id, str(val_uuid)),
            )
            conn.commit()

    # Propose action through action_service with deterministic policy gating
    act_req = ActionProposeRequest(
        scenario_id=scenario_id,
        action_type=req.action_type,
        target_entity_id=req.target_entity_id or order_id,
        payload=req.parameters,
        idempotency_key=f"EXC-ACT-{exception_id}-{uuid.uuid4().hex[:6]}",
    )
    action_rec = propose_action(conn, act_req)

    # If action requires approval, link the approval request
    approval_id: Optional[str] = None
    new_status = "PROPOSED"
    if action_rec.requires_approval:
        new_status = "AWAITING_APPROVAL"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT approval_id FROM approval_requests WHERE action_id = %s ORDER BY requested_at DESC LIMIT 1;",
                (action_rec.action_id,),
            )
            appr_row = cur.fetchone()
            if appr_row:
                approval_id = str(appr_row[0])
            else:
                approval_rec = create_approval_request(
                    conn,
                    required_domain="FINANCE" if "ORDER" in req.action_type or "PURCHASE" in req.action_type else "OPERATIONS",
                    action_id=action_rec.action_id,
                    scenario_id=scenario_id,
                )
                approval_id = approval_rec.approval_id
    else:
        new_status = "APPROVED"

    now = datetime.now(timezone.utc)
    proposed_data = {
        "action_id": action_rec.action_id,
        "action_type": req.action_type,
        "parameters": req.parameters,
        "justification": req.justification,
        "notes": req.notes,
        "requires_approval": action_rec.requires_approval,
        "proposed_by": actor_id,
        "proposed_at": now.isoformat(),
    }

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE operational_exceptions
            SET
                action_id = %s,
                approval_id = %s,
                status = %s,
                proposed_action = %s,
                updated_at = %s
            WHERE exception_id = %s;
            """,
            (
                action_rec.action_id,
                approval_id,
                new_status,
                json.dumps(proposed_data),
                now,
                str(val_uuid),
            ),
        )

        _log_exception_event(
            cur,
            event_type="EXCEPTION_ACTION_PROPOSED",
            status_val=new_status,
            exception_id=str(val_uuid),
            order_id=order_id,
            scenario_id=scenario_id,
            actor_id=actor_id,
            payload={
                "action_id": action_rec.action_id,
                "action_type": req.action_type,
                "requires_approval": action_rec.requires_approval,
                "status": new_status,
            },
        )
        conn.commit()

    return {
        "exception_id": str(val_uuid),
        "status": new_status,
        "action_id": action_rec.action_id,
        "approval_id": approval_id,
        "requires_approval": action_rec.requires_approval,
        "message": "Action proposed successfully" if not action_rec.requires_approval else "Action proposed; human approval required.",
    }


def decide_exception_approval(
    conn,
    exception_id: str,
    decision: str,
    justification: str,
    current_user: AuthUser,
) -> Dict[str, Any]:
    """Approve or reject a pending approval request linked to an operational exception."""
    try:
        val_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exception_id UUID '{exception_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT approval_id, action_id, order_id, scenario_id, status
            FROM operational_exceptions WHERE exception_id = %s;
            """,
            (str(val_uuid),),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exception '{exception_id}' not found.",
            )

        approval_id = row[0]
        if not approval_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exception '{exception_id}' does not have a pending approval request.",
            )

        order_id = row[2]
        scenario_id = str(row[3]) if row[3] else None

    norm_decision = decision.strip().upper()
    dec_req = ApprovalDecisionRequest(
        status=norm_decision,
        decided_by=current_user.user_id,
        reason=justification,
    )
    approval_rec = decide_approval_request(
        conn,
        approval_id=str(approval_id),
        req=dec_req,
    )

    norm_decision = decision.strip().upper()
    new_status = "APPROVED" if norm_decision == "APPROVED" else "REJECTED"
    now = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE operational_exceptions
            SET status = %s, updated_at = %s
            WHERE exception_id = %s;
            """,
            (new_status, now, str(val_uuid)),
        )

        _log_exception_event(
            cur,
            event_type="EXCEPTION_ACTION_DECIDED",
            status_val=new_status,
            exception_id=str(val_uuid),
            order_id=order_id,
            scenario_id=scenario_id,
            actor_id=current_user.user_id,
            payload={
                "approval_id": str(approval_id),
                "decision": new_status,
                "justification": justification,
            },
        )
        conn.commit()

    return {
        "exception_id": str(val_uuid),
        "status": new_status,
        "approval_id": str(approval_id),
        "decision": new_status,
        "message": f"Exception action {new_status.lower()} successfully.",
    }


def execute_exception_action(
    conn,
    exception_id: str,
    caller_id: str = "operator",
) -> ExceptionResolutionResponse:
    """Execute the approved action, mark exception RESOLVED, and update linked order."""
    try:
        val_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exception_id UUID '{exception_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT action_id, order_id, scenario_id, status
            FROM operational_exceptions WHERE exception_id = %s;
            """,
            (str(val_uuid),),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exception '{exception_id}' not found.",
            )

        action_id = row[0]
        if not action_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exception '{exception_id}' does not have a proposed action to execute.",
            )

        order_id = row[1]
        scenario_id = str(row[2]) if row[2] else None

    # Execute action via action_service
    exec_record = execute_action(conn, str(action_id), caller_id=caller_id)

    now = datetime.now(timezone.utc)
    summary = f"Action {str(action_id)} executed successfully by {caller_id}."

    with conn.cursor() as cur:
        # Mark exception RESOLVED
        cur.execute(
            """
            UPDATE operational_exceptions
            SET
                status = 'RESOLVED',
                resolution_notes = %s,
                resolved_at = %s,
                updated_at = %s
            WHERE exception_id = %s;
            """,
            (summary, now, now, str(val_uuid)),
        )

        # Update order in order_processing_queue to COMPLETED
        if order_id:
            cur.execute(
                """
                UPDATE order_processing_queue
                SET status = 'COMPLETED', completed_at = %s, last_error = NULL
                WHERE order_id = %s;
                """,
                (now, order_id),
            )
            cur.execute(
                """
                UPDATE orders
                SET status = 'COMPLETED', updated_at = %s
                WHERE order_id = %s;
                """,
                (now, order_id),
            )

        _log_exception_event(
            cur,
            event_type="EXCEPTION_RESOLVED",
            status_val="RESOLVED",
            exception_id=str(val_uuid),
            order_id=order_id,
            scenario_id=scenario_id,
            actor_id=caller_id,
            payload={
                "action_id": str(action_id),
                "execution_status": exec_record.status,
                "order_id": order_id,
            },
        )
        conn.commit()

    return ExceptionResolutionResponse(
        exception_id=str(val_uuid),
        status="RESOLVED",
        order_id=order_id,
        order_status="COMPLETED" if order_id else None,
        action_id=str(action_id),
        action_status=exec_record.status,
        message="Action executed and exception resolved successfully.",
    )


def resume_order_from_exception(
    conn,
    exception_id: str,
    notes: Optional[str] = None,
    actor_id: str = "operator",
) -> ExceptionResolutionResponse:
    """Manually resolve the exception and return the order to the queue in QUEUED status."""
    try:
        val_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exception_id UUID '{exception_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT order_id, scenario_id, status
            FROM operational_exceptions WHERE exception_id = %s;
            """,
            (str(val_uuid),),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exception '{exception_id}' not found.",
            )

        order_id = row[0]
        scenario_id = str(row[1]) if row[1] else None

        now = datetime.now(timezone.utc)
        res_notes = notes or f"Order resumed by {actor_id}."

        # Mark exception RESOLVED
        cur.execute(
            """
            UPDATE operational_exceptions
            SET
                status = 'RESOLVED',
                resolution_notes = %s,
                resolved_at = %s,
                updated_at = %s
            WHERE exception_id = %s;
            """,
            (res_notes, now, now, str(val_uuid)),
        )

        # Reset order in order_processing_queue to QUEUED with bounded attempt allowance
        if order_id:
            cur.execute(
                """
                UPDATE order_processing_queue
                SET
                    status = 'QUEUED',
                    exception_id = NULL,
                    last_error = NULL,
                    claimed_at = NULL,
                    max_attempts = GREATEST(COALESCE(max_attempts, 3), attempt_count + 1)
                WHERE order_id = %s;
                """,
                (order_id,),
            )
            cur.execute(
                """
                UPDATE orders
                SET status = 'OPEN', updated_at = %s
                WHERE order_id = %s;
                """,
                (now, order_id),
            )
            # Synchronize with orders_queued and orders_running
            cur.execute("DELETE FROM orders_running WHERE order_id = %s;", (order_id,))
            cur.execute(
                """
                INSERT INTO orders_queued (
                    queue_id, order_id, customer_name, product_code, quantity_tons, priority, queue_position, scenario_type
                )
                SELECT gen_random_uuid(), o.order_id, o.customer_ref, COALESCE(ol.product_id, 'PRD-HRC'),
                       COALESCE(ol.requested_qty, 50.0), o.priority, 1, 'NORMAL'
                FROM orders o
                LEFT JOIN order_lines ol ON o.order_id = ol.order_id
                WHERE o.order_id = %s
                ON CONFLICT (order_id) DO UPDATE SET queue_position = 1;
                """,
                (order_id,),
            )

        _log_exception_event(
            cur,
            event_type="ORDER_RESUMED_FROM_EXCEPTION",
            status_val="RESOLVED",
            exception_id=str(val_uuid),
            order_id=order_id,
            scenario_id=scenario_id,
            actor_id=actor_id,
            payload={
                "order_id": order_id,
                "resumed_by": actor_id,
                "notes": res_notes,
            },
        )
        conn.commit()

    return ExceptionResolutionResponse(
        exception_id=str(val_uuid),
        status="RESOLVED",
        order_id=order_id,
        order_status="OPEN" if order_id else None,
        action_id=None,
        action_status=None,
        message=f"Order {order_id} returned to pending queue; exception resolved.",
    )
