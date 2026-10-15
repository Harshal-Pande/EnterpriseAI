"""Scheduler management API endpoints.

Provides:
- GET /api/scheduler/status : Read-only scheduler state, lease status, and cycle history
- POST /api/scheduler/trigger : On-demand execution of an eligible scenario cycle
- GET /api/scheduler/templates : List available scenario templates with metadata
- GET /api/scheduler/scenarios : Paginated list of persistent scenario instances
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.services.scheduler_service import default_scheduler

logger = logging.getLogger("enterpriseai.api.scheduler")

router = APIRouter()


@router.get("/status")
def get_scheduler_status(conn=Depends(get_db)) -> Dict[str, Any]:
    """Retrieve observable status, lease locking state, and last outcome of the scenario scheduler."""
    st = default_scheduler.get_status(conn)
    st["running"] = st.get("is_running", False)
    return st


@router.post("/trigger", status_code=status.HTTP_200_OK)
def trigger_scheduler_cycle(
    force: bool = Query(False, description="Administrative override to bypass queue capacity (ADMIN only)"),
    admin_override: bool = Query(False, description="Explicit administrative override to bypass queue capacity (ADMIN only)"),
    override_reason: Optional[str] = Query(None, description="Mandatory audit justification when admin_override or force is requested"),
    template_id: Optional[str] = Query(None, description="Specific scenario template ID to trigger"),
    idempotency_key: Optional[str] = Query(None, description="Optional idempotency key"),
    seed: Optional[int] = Query(None, description="Deterministic seed for template selection"),
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger a scheduler cycle to execute the next eligible scenario."""
    is_override = admin_override or force
    if is_override:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative override requires ADMIN role.",
            )
        if not override_reason or not override_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrative override requires a non-empty override_reason.",
            )

    return default_scheduler.run_cycle(
        conn,
        force=force,
        admin_override=admin_override,
        override_reason=override_reason,
        template_id=template_id,
        idempotency_key=idempotency_key,
        seed=seed,
        is_manual=True,
        actor_id=current_user.user_id,
    )


@router.post("/recover", status_code=status.HTTP_200_OK)
def recover_stale_scenarios(
    timeout_seconds: Optional[int] = Query(None, ge=1, description="Stale timeout threshold in seconds"),
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    """Trigger manual recovery of orphaned or stale queued/running scenarios."""
    recovered_ids = default_scheduler.recover_orphaned_workflows(conn, stale_timeout_seconds=timeout_seconds)
    return {
        "recovered_count": len(recovered_ids),
        "recovered_scenario_ids": recovered_ids,
    }


@router.get("/templates")
def list_scenario_templates(
    domain: Optional[str] = Query(None, description="Filter by domain (Inventory, Procurement, etc.)"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    conn=Depends(get_db),
) -> List[Dict[str, Any]]:
    """List available scenario templates with metadata."""
    clauses = ["enabled = TRUE"]
    params: list = []
    if domain:
        clauses.append("domain ILIKE %s")
        params.append(domain)
    if severity:
        clauses.append("severity = %s")
        params.append(severity.upper())

    sql = f"""
        SELECT
            scenario_template_id, scenario_type, domain, severity,
            description, injection_method, agents_involved, expected_response, guardrail
        FROM scenario_templates
        WHERE {' AND '.join(clauses)}
        ORDER BY scenario_template_id ASC;
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [
            {
                "template_id": r[0],
                "scenario_template_id": r[0],
                "scenario_type": r[1],
                "domain": r[2],
                "severity": r[3],
                "description": r[4],
                "injection_method": r[5],
                "agents_involved": r[6],
                "expected_response": r[7],
                "guardrail": r[8],
            }
            for r in rows
        ]


@router.get("/scenarios")
def list_scheduler_scenarios(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db),
) -> List[Dict[str, Any]]:
    """List persisted scenario instances with filtering and deterministic pagination."""
    clauses: list[str] = []
    params: list = []
    if status_filter:
        clauses.append("status = %s")
        params.append(status_filter.upper())
    if severity:
        clauses.append("severity = %s")
        params.append(severity.upper())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            scenario_id, scenario_template_id, scheduled_at, created_at,
            status, severity, linked_order_id, linked_batch_id,
            input_overlay, idempotency_key, updated_at
        FROM scenario_instances
        {where_sql}
        ORDER BY created_at DESC, scenario_id DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [
            {
                "scenario_id": str(r[0]),
                "template_id": r[1],
                "scenario_template_id": r[1],
                "scheduled_at": r[2].isoformat() if r[2] else None,
                "created_at": r[3].isoformat() if r[3] else None,
                "status": r[4],
                "severity": r[5],
                "linked_order_id": r[6],
                "linked_batch_id": r[7],
                "input_overlay": r[8] if isinstance(r[8], dict) else {},
                "idempotency_key": r[9],
                "updated_at": r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ]
