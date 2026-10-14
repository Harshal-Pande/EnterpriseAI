"""Agent run persistence service for specialist-agent executions.

Provides durable PostgreSQL records for agent runs linked to workflows (scenario_instances).
Records input, output, evidence references, execution timing, duration, and sanitized errors.
Maintains clear distinction between deterministic execution and external model calls.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException, status

from app.core.sanitizer import sanitize_dict, sanitize_error_message
from app.models.agent_run import (
    ALLOWED_AGENT_STATUSES,
    AgentRunComplete,
    AgentRunCreate,
    AgentRunFail,
    AgentRunRecord,
)

logger = logging.getLogger("enterpriseai.agents")


def _row_to_agent_run_record(row: tuple) -> AgentRunRecord:
    """Convert agent_runs DB row tuple to AgentRunRecord Pydantic model."""
    (
        agent_run_id,
        scenario_id,
        workflow_run_id,
        agent_name,
        started_at,
        completed_at,
        run_status,
        input_refs,
        output,
        evidence_refs,
        error_code,
        model_provider,
        model_name,
        prompt_version,
        error_message,
    ) = row

    duration_seconds: Optional[float] = None
    if started_at and completed_at:
        duration_seconds = round((completed_at - started_at).total_seconds(), 4)

    return AgentRunRecord(
        agent_run_id=str(agent_run_id),
        scenario_id=str(scenario_id),
        workflow_run_id=str(workflow_run_id),
        agent_name=str(agent_name),
        status=str(run_status),
        started_at=started_at.isoformat() if started_at else "",
        completed_at=completed_at.isoformat() if completed_at else None,
        duration_seconds=duration_seconds,
        input_refs=input_refs if (isinstance(input_refs, (list, dict))) else [],
        output=output if (isinstance(output, (list, dict))) else None,
        evidence_refs=evidence_refs if isinstance(evidence_refs, list) else [],
        error_code=str(error_code) if error_code else None,
        error_message=str(error_message) if error_message else None,
        model_provider=str(model_provider) if model_provider else None,
        model_name=str(model_name) if model_name else None,
        prompt_version=str(prompt_version) if prompt_version else None,
    )


def start_agent_run(conn, req: AgentRunCreate) -> AgentRunRecord:
    """Create a persistent agent-run record in RUNNING status linked to a workflow."""
    try:
        val_scenario_uuid = uuid.UUID(req.scenario_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario_id UUID: '{req.scenario_id}'",
        )

    with conn.cursor() as cur:
        # Verify scenario exists and fetch workflow_run_id if not supplied
        cur.execute(
            "SELECT scenario_id, workflow_run_id FROM scenario_instances WHERE scenario_id = %s;",
            (str(val_scenario_uuid),),
        )
        parent = cur.fetchone()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow scenario '{req.scenario_id}' not found.",
            )

        workflow_run_id = req.workflow_run_id or str(parent[1] or parent[0])
        try:
            val_wf_uuid = uuid.UUID(workflow_run_id)
        except ValueError:
            val_wf_uuid = val_scenario_uuid

        agent_run_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        sanitized_input = sanitize_dict(req.input_refs)

        cur.execute(
            """
            INSERT INTO agent_runs (
                agent_run_id, scenario_id, workflow_run_id, agent_name,
                started_at, status, input_refs, output, evidence_refs,
                error_code, model_provider, model_name, prompt_version, error_message
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING
                agent_run_id, scenario_id, workflow_run_id, agent_name,
                started_at, completed_at, status, input_refs, output,
                evidence_refs, error_code, model_provider, model_name,
                prompt_version, error_message;
            """,
            (
                str(agent_run_id),
                str(val_scenario_uuid),
                str(val_wf_uuid),
                req.agent_name.strip(),
                now,
                "RUNNING",
                json.dumps(sanitized_input),
                None,
                json.dumps([]),
                None,
                req.model_provider or "deterministic",
                req.model_name or "scripted-agent-v1",
                req.prompt_version or "v1.0",
                None,
            ),
        )
        row = cur.fetchone()
        conn.commit()

        return _row_to_agent_run_record(row)


def complete_agent_run(conn, agent_run_id: str, req: AgentRunComplete) -> AgentRunRecord:
    """Mark an existing agent run as COMPLETED with structured output."""
    try:
        val_run_uuid = uuid.UUID(agent_run_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent_run_id UUID: '{agent_run_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT agent_run_id, status FROM agent_runs
            WHERE agent_run_id = %s FOR UPDATE;
            """,
            (str(val_run_uuid),),
        )
        current = cur.fetchone()
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent run '{agent_run_id}' not found.",
            )

        now = datetime.now(timezone.utc)
        sanitized_output = sanitize_dict(req.output) if req.output is not None else {}
        sanitized_evidence = sanitize_dict(req.evidence_refs) if req.evidence_refs else []

        cur.execute(
            """
            UPDATE agent_runs
            SET
                status = 'COMPLETED',
                completed_at = %s,
                output = %s,
                evidence_refs = %s
            WHERE agent_run_id = %s
            RETURNING
                agent_run_id, scenario_id, workflow_run_id, agent_name,
                started_at, completed_at, status, input_refs, output,
                evidence_refs, error_code, model_provider, model_name,
                prompt_version, error_message;
            """,
            (now, json.dumps(sanitized_output), json.dumps(sanitized_evidence), str(val_run_uuid)),
        )
        row = cur.fetchone()
        conn.commit()

        return _row_to_agent_run_record(row)


def fail_agent_run(conn, agent_run_id: str, req: AgentRunFail) -> AgentRunRecord:
    """Mark an existing agent run as FAILED with sanitized error message."""
    try:
        val_run_uuid = uuid.UUID(agent_run_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent_run_id UUID: '{agent_run_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT agent_run_id, status FROM agent_runs
            WHERE agent_run_id = %s FOR UPDATE;
            """,
            (str(val_run_uuid),),
        )
        current = cur.fetchone()
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent run '{agent_run_id}' not found.",
            )

        now = datetime.now(timezone.utc)
        sanitized_err_msg = sanitize_error_message(req.error_message or "Unknown execution error")
        sanitized_evidence = sanitize_dict(req.evidence_refs) if req.evidence_refs else []

        cur.execute(
            """
            UPDATE agent_runs
            SET
                status = 'FAILED',
                completed_at = %s,
                error_code = %s,
                error_message = %s,
                evidence_refs = %s
            WHERE agent_run_id = %s
            RETURNING
                agent_run_id, scenario_id, workflow_run_id, agent_name,
                started_at, completed_at, status, input_refs, output,
                evidence_refs, error_code, model_provider, model_name,
                prompt_version, error_message;
            """,
            (
                now,
                req.error_code or "EXECUTION_ERROR",
                sanitized_err_msg,
                json.dumps(sanitized_evidence),
                str(val_run_uuid),
            ),
        )
        row = cur.fetchone()
        conn.commit()

        return _row_to_agent_run_record(row)


def get_agent_run(conn, agent_run_id: str) -> Optional[AgentRunRecord]:
    """Retrieve persistent agent-run record by UUID."""
    try:
        val_uuid = uuid.UUID(agent_run_id)
    except ValueError:
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                agent_run_id, scenario_id, workflow_run_id, agent_name,
                started_at, completed_at, status, input_refs, output,
                evidence_refs, error_code, model_provider, model_name,
                prompt_version, error_message
            FROM agent_runs
            WHERE agent_run_id = %s;
            """,
            (str(val_uuid),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return _row_to_agent_run_record(row)


def list_agent_runs(
    conn,
    scenario_id: Optional[str] = None,
    workflow_run_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[AgentRunRecord], int]:
    """List persistent agent runs with deterministic pagination and ordering."""
    clauses: list[str] = []
    params: list[Any] = []

    effective_workflow = scenario_id or workflow_run_id
    if effective_workflow:
        clauses.append("(ar.scenario_id = %s OR ar.workflow_run_id = %s)")
        params.extend([effective_workflow, effective_workflow])

    if agent_name:
        clauses.append("LOWER(ar.agent_name) = LOWER(%s)")
        params.append(agent_name.strip())

    if status_filter:
        clauses.append("ar.status = %s")
        params.append(status_filter.upper().strip())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            ar.agent_run_id, ar.scenario_id, ar.workflow_run_id, ar.agent_name,
            ar.started_at, ar.completed_at, ar.status, ar.input_refs, ar.output,
            ar.evidence_refs, ar.error_code, ar.model_provider, ar.model_name,
            ar.prompt_version, ar.error_message,
            COUNT(*) OVER() AS total_count
        FROM agent_runs ar
        {where_sql}
        ORDER BY ar.started_at DESC, ar.agent_run_id DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        return [], 0

    total = rows[0][15]
    items = [_row_to_agent_run_record(r[:15]) for r in rows]
    return items, total
