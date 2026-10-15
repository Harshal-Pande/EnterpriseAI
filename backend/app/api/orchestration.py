"""Governed Orchestration API Endpoints (Phase 4).

Provides:
- POST /api/orchestration/execute : Launch a governed multi-agent orchestration pipeline
- POST /api/orchestration/{workflow_id}/run : Run pipeline for an existing workflow
- POST /api/orchestration/{workflow_id}/retry : Safely retry or resume a workflow
- GET  /api/orchestration/{workflow_id} : Get current status and decision summary
- GET  /api/orchestration/{workflow_id}/agents : Get individual agent execution steps
- GET  /api/orchestration/{workflow_id}/governance : Inspect policy evaluations and approval status
- GET  /api/orchestration/providers : Get active LLM provider configuration
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.llm_provider import get_default_provider
from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.models.workflow import (
    WorkflowCreateRequest,
    WorkflowInstance,
)
from app.orchestration.governed import GovernedOrchestrator, OrchestrationResult
from app.services.workflow_service import create_workflow, get_workflow

logger = logging.getLogger("enterpriseai.api.orchestration")

router = APIRouter()


@router.post("/execute", response_model=OrchestrationResult, status_code=status.HTTP_200_OK)
def execute_governed_orchestration(
    order_id: str = Query("ORD-1042", description="Order ID to process"),
    template_id: str = Query("TPL-010", description="Scenario template ID"),
    severity: str = Query("MEDIUM", description="Severity level: LOW, MEDIUM, HIGH, CRITICAL"),
    idempotency_key: Optional[str] = Query(None, description="Idempotency key to prevent duplicate runs"),
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Launch a governed multi-agent orchestration pipeline.

    1. Checks idempotency (if idempotency_key is provided).
    2. Creates a durable workflow instance in PostgreSQL.
    3. Executes specialist agents through grounded evidence gates.
    4. Evaluates recommendations via the deterministic policy engine.
    5. Gates execution on required human approvals.
    6. Persists audit and decision trails.
    """
    idemp_key = idempotency_key or f"ORCH-{order_id}-{template_id}-{severity}"

    # Idempotency check: see if workflow with this key already exists
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT scenario_id, status, resolution_summary, linked_order_id
            FROM scenario_instances
            WHERE idempotency_key = %s;
            """,
            (idemp_key,),
        )
        existing = cur.fetchone()
        if existing:
            # If already resolved or running, return existing state
            existing_id = str(existing[0])
            existing_status = str(existing[1])
            if existing_status in ("RESOLVED", "COMPLETED", "WAITING_APPROVAL"):
                return GovernedOrchestrator().execute(
                    workflow_id=existing_id,
                    order_id=existing[3] or order_id,
                    conn=conn,
                    scenario_id=existing_id,
                )

    # Create a new workflow instance
    req = WorkflowCreateRequest(
        scenario_template_id=template_id,
        linked_order_id=order_id,
        severity=severity,
        idempotency_key=idemp_key,
        execute_immediately=False,
        data_mode="SYNTHETIC",
    )
    instance = create_workflow(conn, req)

    # Execute governed orchestration pipeline
    orchestrator = GovernedOrchestrator()
    result = orchestrator.execute(
        workflow_id=instance.workflow_id,
        order_id=order_id,
        conn=conn,
        scenario_id=instance.scenario_id,
    )

    return result


@router.post("/{workflow_id}/run", response_model=OrchestrationResult)
def run_orchestration_for_workflow(
    workflow_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Execute governed orchestration for an existing workflow instance."""
    instance = get_workflow(conn, workflow_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow instance '{workflow_id}' not found.",
        )

    orchestrator = GovernedOrchestrator()
    result = orchestrator.execute(
        workflow_id=instance.workflow_id,
        order_id=instance.linked_order_id or "ORD-UNKNOWN",
        conn=conn,
        scenario_id=instance.scenario_id,
    )

    return result


@router.post("/{workflow_id}/retry", response_model=OrchestrationResult)
def retry_or_resume_workflow(
    workflow_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Safely retry a failed workflow or resume an approval-gated workflow.

    - If WAITING_APPROVAL and approved: executes the queued action safely.
    - If WAITING_APPROVAL and still pending: reports approval requirement.
    - If FAILED: re-executes the pipeline.
    - If RESOLVED: returns without re-execution (idempotent safeguard).
    """
    orchestrator = GovernedOrchestrator()
    return orchestrator.retry(workflow_id=workflow_id, conn=conn)


@router.get("/providers")
def get_provider_info(
    current_user: AuthUser = Depends(require_role(UserRole.VIEWER)),
):
    """Return information about the active LLM provider configuration."""
    provider = get_default_provider()
    mode = provider.get_mode().value
    is_sim = mode == "SIMULATION"

    gemini_keys_count = len(provider.gemini_keys) if hasattr(provider, "gemini_keys") else 0
    openrouter_enabled = (
        provider.openrouter_config.enabled if hasattr(provider, "openrouter_config") else False
    )
    openrouter_model = (
        provider.openrouter_config.model_name if hasattr(provider, "openrouter_config") else None
    )

    return {
        "mode": mode,
        "model_name": provider.get_model_name(),
        "is_simulation": is_sim,
        "gemini_keys_configured": gemini_keys_count,
        "openrouter_enabled": openrouter_enabled,
        "openrouter_model": openrouter_model,
        "description": (
            "Deterministic simulation provider — generates structured recommendations "
            "grounded in PostgreSQL evidence without external API calls."
            if is_sim
            else f"Live LLM provider — connects to Gemini ({gemini_keys_count} keys in cyclic pool) with OpenRouter fallback (enabled={openrouter_enabled})."
        ),
    }


@router.get("/{workflow_id}", response_model=Dict[str, Any])
def get_orchestration_status(
    workflow_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.VIEWER)),
    conn=Depends(get_db),
):
    """Retrieve current status, decision summary, and recommendation for a workflow."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.scenario_id, s.scenario_template_id, s.status, s.severity,
                s.linked_order_id, s.created_at, s.resolved_at, s.resolution_summary,
                d.decision_id, d.decision_code, d.supervisor_summary,
                d.recommended_action, d.human_approval_required, d.approval_status
            FROM scenario_instances s
            LEFT JOIN decisions d ON s.scenario_id = d.scenario_id
            WHERE s.scenario_id = %s;
            """,
            (workflow_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found.",
            )

        (
            scen_id, tpl_id, status_val, severity,
            order_id, created_at, resolved_at, res_summary,
            decision_id, decision_code, sup_summary,
            rec_action, human_app_req, app_status,
        ) = row

        return {
            "workflow_id": str(scen_id),
            "template_id": tpl_id,
            "status": status_val,
            "severity": severity,
            "order_id": order_id,
            "created_at": created_at.isoformat() if created_at else None,
            "resolved_at": resolved_at.isoformat() if resolved_at else None,
            "resolution_summary": res_summary,
            "decision": {
                "decision_id": str(decision_id) if decision_id else None,
                "decision_code": decision_code,
                "summary": sup_summary,
                "recommended_action": rec_action if isinstance(rec_action, dict) else {},
                "human_approval_required": bool(human_app_req) if human_app_req is not None else False,
                "approval_status": app_status,
            } if decision_id else None,
            "can_retry": status_val in ("FAILED", "WAITING_APPROVAL"),
        }


@router.get("/{workflow_id}/agents", response_model=List[Dict[str, Any]])
def get_workflow_agent_runs(
    workflow_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.VIEWER)),
    conn=Depends(get_db),
):
    """Retrieve individual agent execution results from agent_runs for this workflow."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                agent_run_id, agent_name, started_at, completed_at, status,
                output, error_code, model_provider, model_name
            FROM agent_runs
            WHERE scenario_id = %s
            ORDER BY started_at ASC;
            """,
            (workflow_id,),
        )
        runs = cur.fetchall()

        results = []
        for r in runs:
            out = r[5]
            if isinstance(out, str):
                try:
                    out = json.loads(out)
                except Exception:
                    out = {}
            results.append({
                "agent_run_id": str(r[0]),
                "agent_name": r[1],
                "started_at": r[2].isoformat() if r[2] else None,
                "completed_at": r[3].isoformat() if r[3] else None,
                "status": r[4],
                "output": out if isinstance(out, dict) else {},
                "error_code": r[6],
                "model_provider": r[7],
                "model_name": r[8],
            })
        return results


@router.get("/{workflow_id}/governance", response_model=Dict[str, Any])
def get_workflow_governance(
    workflow_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.VIEWER)),
    conn=Depends(get_db),
):
    """Retrieve policy evaluations, approval requests, and queued actions for a workflow."""
    with conn.cursor() as cur:
        # Policy evaluations
        cur.execute(
            """
            SELECT pe.policy_eval_id, pe.rule_id, pe.result, pe.details, pe.evaluated_at
            FROM policy_evaluations pe
            JOIN decisions d ON pe.decision_id = d.decision_id
            WHERE d.scenario_id = %s
            ORDER BY pe.evaluated_at ASC;
            """,
            (workflow_id,),
        )
        evals = [
            {
                "eval_id": str(r[0]),
                "rule_id": r[1],
                "result": r[2],
                "details": r[3] if isinstance(r[3], dict) else {},
                "evaluated_at": r[4].isoformat() if r[4] else None,
            }
            for r in cur.fetchall()
        ]

        # Approval requests
        cur.execute(
            """
            SELECT approval_id, required_domain, status, decided_by, decided_at, reason
            FROM approval_requests
            WHERE scenario_id = %s
            ORDER BY requested_at DESC;
            """,
            (workflow_id,),
        )
        approvals = [
            {
                "approval_id": str(r[0]),
                "required_domain": r[1],
                "status": r[2],
                "decided_by": r[3],
                "decided_at": r[4].isoformat() if r[4] else None,
                "reason": r[5],
            }
            for r in cur.fetchall()
        ]

        # Actions
        cur.execute(
            """
            SELECT action_id, action_type, status, requires_approval, approved_by, result
            FROM action_queue
            WHERE scenario_id = %s
            ORDER BY created_at DESC;
            """,
            (workflow_id,),
        )
        actions = [
            {
                "action_id": str(r[0]),
                "action_type": r[1],
                "status": r[2],
                "requires_approval": r[3],
                "approved_by": r[4],
                "result": r[5] if isinstance(r[5], dict) else {},
            }
            for r in cur.fetchall()
        ]

        return {
            "workflow_id": workflow_id,
            "policy_evaluations": evals,
            "approval_requests": approvals,
            "actions": actions,
        }
