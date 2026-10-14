"""Workflow management service with durable PostgreSQL persistence and state transitions.

Adheres to:
- scenario_instances and scenario_templates tables in 002_runtime_schema.sql
- Explicit status transition validation
- Complete audit trail logging into event_log for all transitions
- Input and error sanitization to prevent leaking credentials
- Idempotency preservation
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException, status

from app.core.sanitizer import sanitize_dict, sanitize_error_message
from app.models.workflow import (
    ALLOWED_WORKFLOW_STATUSES,
    TERMINAL_STATUSES,
    WorkflowCreateRequest,
    WorkflowInstance,
    WorkflowTransitionRequest,
    validate_status_transition,
)

logger = logging.getLogger("enterpriseai.workflow")


def trigger_workflow(order_id: str, conn=None) -> dict:
    """Trigger a workflow for an order. Supports optional persistent execution."""
    if conn:
        req = WorkflowCreateRequest(
            scenario_template_id="TPL-010",
            linked_order_id=order_id,
            execute_immediately=True,
        )
        instance = create_workflow(conn, req)
        return {"status": "started", "workflow_id": instance.workflow_id}
    return {"status": "started", "workflow_id": f"WF-{order_id}"}


def _compute_payload_hash(data: dict) -> str:
    """Compute deterministic SHA-256 hash of payload."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _row_to_workflow_instance(row: tuple, agent_runs_count: int = 0) -> WorkflowInstance:
    """Convert scenario_instances DB row tuple to WorkflowInstance Pydantic model."""
    (
        scenario_id,
        scenario_template_id,
        scheduled_at,
        created_at,
        wf_status,
        severity,
        linked_order_id,
        linked_batch_id,
        input_overlay,
        workflow_run_id,
        resolved_at,
        resolution_summary,
        idempotency_key,
        data_mode,
        updated_at,
    ) = row

    # Derive human-friendly current_agent based on status
    current_agent = "SupervisorAgent"
    if wf_status in {"RUNNING", "INVESTIGATING"}:
        current_agent = "InventoryAgent"
    elif wf_status == "WAITING_APPROVAL":
        current_agent = "FinanceAgent"
    elif wf_status == "RESOLVED":
        current_agent = "SupervisorAgent"

    return WorkflowInstance(
        workflow_id=str(scenario_id),
        scenario_id=str(scenario_id),
        workflow_run_id=str(workflow_run_id or scenario_id),
        scenario_template_id=str(scenario_template_id),
        status=str(wf_status),
        severity=str(severity),
        linked_order_id=str(linked_order_id) if linked_order_id else None,
        linked_batch_id=str(linked_batch_id) if linked_batch_id else None,
        input_overlay=input_overlay if isinstance(input_overlay, dict) else {},
        resolution_summary=resolution_summary,
        idempotency_key=str(idempotency_key),
        data_mode=str(data_mode),
        created_at=created_at.isoformat() if created_at else "",
        scheduled_at=scheduled_at.isoformat() if scheduled_at else "",
        updated_at=updated_at.isoformat() if updated_at else (created_at.isoformat() if created_at else ""),
        resolved_at=resolved_at.isoformat() if resolved_at else None,
        current_agent=current_agent,
        agent_runs_count=agent_runs_count,
    )


def create_workflow(conn, req: WorkflowCreateRequest) -> WorkflowInstance:
    """Create and persist a new workflow instance in PostgreSQL with audit log.

    Supports idempotency key: if idempotency_key already exists, returns existing instance.
    """
    with conn.cursor() as cur:
        # Check idempotency if key provided
        if req.idempotency_key:
            cur.execute(
                """
                SELECT
                    scenario_id, scenario_template_id, scheduled_at, created_at,
                    status, severity, linked_order_id, linked_batch_id,
                    input_overlay, workflow_run_id, resolved_at, resolution_summary,
                    idempotency_key, data_mode, updated_at
                FROM scenario_instances
                WHERE idempotency_key = %s;
                """,
                (req.idempotency_key,),
            )
            existing = cur.fetchone()
            if existing:
                logger.info("Workflow with idempotency_key '%s' already exists; returning existing.", req.idempotency_key)
                return _row_to_workflow_instance(existing)

        # Validate scenario_template_id exists
        cur.execute(
            "SELECT scenario_template_id, severity FROM scenario_templates WHERE scenario_template_id = %s;",
            (req.scenario_template_id,),
        )
        tpl = cur.fetchone()
        if not tpl:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scenario template '{req.scenario_template_id}' does not exist.",
            )

        scenario_id = uuid.uuid4()
        workflow_run_id = scenario_id
        now = datetime.now(timezone.utc)
        idempotency_key = req.idempotency_key or f"WF-{scenario_id}"
        severity = req.severity.upper() if req.severity else tpl[1]
        sanitized_overlay = sanitize_dict(req.input_overlay or {})

        try:
            cur.execute(
                """
                INSERT INTO scenario_instances (
                    scenario_id, scenario_template_id, scheduled_at, created_at,
                    status, severity, linked_order_id, linked_batch_id,
                    input_overlay, workflow_run_id, idempotency_key, data_mode, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    scenario_id, scenario_template_id, scheduled_at, created_at,
                    status, severity, linked_order_id, linked_batch_id,
                    input_overlay, workflow_run_id, resolved_at, resolution_summary,
                    idempotency_key, data_mode, updated_at;
                """,
                (
                    str(scenario_id),
                    req.scenario_template_id,
                    now,
                    now,
                    "QUEUED",
                    severity,
                    req.linked_order_id,
                    req.linked_batch_id,
                    json.dumps(sanitized_overlay),
                    str(workflow_run_id),
                    idempotency_key,
                    req.data_mode.upper(),
                    now,
                ),
            )
            row = cur.fetchone()
        except Exception as exc:
            if "idempotency_key" in str(exc).lower() or "unique constraint" in str(exc).lower():
                conn.rollback()
                with conn.cursor() as retry_cur:
                    retry_cur.execute(
                        """
                        SELECT
                            scenario_id, scenario_template_id, scheduled_at, created_at,
                            status, severity, linked_order_id, linked_batch_id,
                            input_overlay, workflow_run_id, resolved_at, resolution_summary,
                            idempotency_key, data_mode, updated_at
                        FROM scenario_instances
                        WHERE idempotency_key = %s;
                        """,
                        (idempotency_key,),
                    )
                    existing_row = retry_cur.fetchone()
                    if existing_row:
                        return _row_to_workflow_instance(existing_row)
            raise

        # Record audit event in event_log
        event_id = uuid.uuid4()
        audit_payload = {
            "workflow_id": str(scenario_id),
            "template_id": req.scenario_template_id,
            "order_id": req.linked_order_id,
            "status": "QUEUED",
        }
        payload_hash = _compute_payload_hash(audit_payload)
        cur.execute(
            """
            INSERT INTO event_log (
                event_id, event_timestamp, event_type, entity_type, entity_id,
                scenario_id, workflow_run_id, actor_type, actor_id, status,
                reason_code, evidence_refs, payload_hash, source_channel
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                str(event_id),
                now,
                "WORKFLOW_CREATED",
                "WORKFLOW",
                str(scenario_id),
                str(scenario_id),
                str(workflow_run_id),
                "SYSTEM",
                "WorkflowEngine",
                "QUEUED",
                "INITIALIZED",
                json.dumps([{"template_id": req.scenario_template_id, "severity": severity}]),
                payload_hash,
                "SYSTEM",
            ),
        )
        conn.commit()

        return _row_to_workflow_instance(row)


def get_workflow(conn, workflow_id_or_ref: str) -> Optional[WorkflowInstance]:
    """Retrieve persistent workflow instance by UUID or reference."""
    with conn.cursor() as cur:
        # Check if valid UUID
        is_uuid = False
        try:
            val_uuid = uuid.UUID(workflow_id_or_ref)
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            cur.execute(
                """
                SELECT
                    si.scenario_id, si.scenario_template_id, si.scheduled_at, si.created_at,
                    si.status, si.severity, si.linked_order_id, si.linked_batch_id,
                    si.input_overlay, si.workflow_run_id, si.resolved_at, si.resolution_summary,
                    si.idempotency_key, si.data_mode, si.updated_at,
                    COUNT(ar.agent_run_id) AS run_count
                FROM scenario_instances si
                LEFT JOIN agent_runs ar ON si.scenario_id = ar.scenario_id
                WHERE si.scenario_id = %s OR si.workflow_run_id = %s
                GROUP BY si.scenario_id;
                """,
                (str(val_uuid), str(val_uuid)),
            )
        else:
            cur.execute(
                """
                SELECT
                    si.scenario_id, si.scenario_template_id, si.scheduled_at, si.created_at,
                    si.status, si.severity, si.linked_order_id, si.linked_batch_id,
                    si.input_overlay, si.workflow_run_id, si.resolved_at, si.resolution_summary,
                    si.idempotency_key, si.data_mode, si.updated_at,
                    COUNT(ar.agent_run_id) AS run_count
                FROM scenario_instances si
                LEFT JOIN agent_runs ar ON si.scenario_id = ar.scenario_id
                WHERE si.linked_order_id = %s OR si.idempotency_key = %s
                GROUP BY si.scenario_id;
                """,
                (workflow_id_or_ref, workflow_id_or_ref),
            )

        row = cur.fetchone()
        if not row:
            return None

        data_row = row[:15]
        run_count = row[15]
        return _row_to_workflow_instance(data_row, agent_runs_count=run_count)


def list_workflows(
    conn,
    status_filter: Optional[str] = None,
    template_id: Optional[str] = None,
    order_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[WorkflowInstance], int]:
    """List persistent workflow instances with deterministic pagination and ordering."""
    clauses: list[str] = []
    params: list[Any] = []

    if status_filter:
        clauses.append("si.status = %s")
        params.append(status_filter.upper().strip())

    if template_id:
        clauses.append("si.scenario_template_id = %s")
        params.append(template_id.strip())

    if order_id:
        clauses.append("si.linked_order_id = %s")
        params.append(order_id.strip())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            si.scenario_id, si.scenario_template_id, si.scheduled_at, si.created_at,
            si.status, si.severity, si.linked_order_id, si.linked_batch_id,
            si.input_overlay, si.workflow_run_id, si.resolved_at, si.resolution_summary,
            si.idempotency_key, si.data_mode, si.updated_at,
            COUNT(ar.agent_run_id) AS run_count,
            COUNT(*) OVER() AS total_count
        FROM scenario_instances si
        LEFT JOIN agent_runs ar ON si.scenario_id = ar.scenario_id
        {where_sql}
        GROUP BY si.scenario_id
        ORDER BY si.created_at DESC, si.scenario_id DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        return [], 0

    total = rows[0][16]
    items = [_row_to_workflow_instance(r[:15], agent_runs_count=r[15]) for r in rows]
    return items, total


def transition_workflow_status(
    conn,
    scenario_id: str,
    req: WorkflowTransitionRequest,
) -> WorkflowInstance:
    """Transition workflow instance to a new status with validation and audit logging."""
    try:
        val_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario_id UUID format: '{scenario_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                scenario_id, scenario_template_id, scheduled_at, created_at,
                status, severity, linked_order_id, linked_batch_id,
                input_overlay, workflow_run_id, resolved_at, resolution_summary,
                idempotency_key, data_mode, updated_at
            FROM scenario_instances
            WHERE scenario_id = %s
            FOR UPDATE;
            """,
            (str(val_uuid),),
        )
        current = cur.fetchone()
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow instance '{scenario_id}' not found.",
            )

        current_status = current[4]
        target_status = req.new_status.upper()

        is_valid, validation_msg = validate_status_transition(current_status, target_status)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_msg,
            )

        now = datetime.now(timezone.utc)
        sanitized_summary = sanitize_error_message(req.resolution_summary) if req.resolution_summary else current[11]
        resolved_at = now if target_status in TERMINAL_STATUSES else current[10]

        cur.execute(
            """
            UPDATE scenario_instances
            SET
                status = %s,
                updated_at = %s,
                resolved_at = %s,
                resolution_summary = %s
            WHERE scenario_id = %s
            RETURNING
                scenario_id, scenario_template_id, scheduled_at, created_at,
                status, severity, linked_order_id, linked_batch_id,
                input_overlay, workflow_run_id, resolved_at, resolution_summary,
                idempotency_key, data_mode, updated_at;
            """,
            (target_status, now, resolved_at, sanitized_summary, str(val_uuid)),
        )
        updated_row = cur.fetchone()

        # Audit event into event_log
        event_id = uuid.uuid4()
        evidence = [
            {
                "previous_status": current_status,
                "new_status": target_status,
                "reason": req.reason_code,
                "note": sanitize_error_message(req.note or ""),
            }
        ]
        audit_payload = {
            "workflow_id": str(val_uuid),
            "previous_status": current_status,
            "new_status": target_status,
            "timestamp": now.isoformat(),
        }
        payload_hash = _compute_payload_hash(audit_payload)

        cur.execute(
            """
            INSERT INTO event_log (
                event_id, event_timestamp, event_type, entity_type, entity_id,
                scenario_id, workflow_run_id, actor_type, actor_id, status,
                reason_code, evidence_refs, payload_hash, source_channel
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                str(event_id),
                now,
                "WORKFLOW_TRANSITION",
                "WORKFLOW",
                str(val_uuid),
                str(val_uuid),
                str(current[9] or val_uuid),
                req.actor_type.upper() if req.actor_type else "SYSTEM",
                req.actor_id or "WorkflowEngine",
                target_status,
                req.reason_code or "STATUS_CHANGE",
                json.dumps(evidence),
                payload_hash,
                "SYSTEM",
            ),
        )
        conn.commit()

        return _row_to_workflow_instance(updated_row)
