"""Controlled Action Execution Service (Task 11).

Manages the lifecycle of proposed, approved, and executed actions in PostgreSQL.
Enforces execution gates:
1. Valid payload and schema.
2. Deterministic policy evaluation.
3. Approval requirement gating (unapproved actions cannot execute).
4. Precondition revalidation immediately before execution.
5. Idempotent execution (duplicate calls do not re-execute side effects).
6. Execution results and attempts persisted in action_execution_results.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.core.events import EventChannel, EventType, default_event_manager
from app.core.sanitizer import sanitize_dict, sanitize_error_message
from app.models.action import (
    ActionDetailResponse,
    ActionExecutionResultRecord,
    ActionProposeRequest,
    ActionRecord,
)
from app.models.policy import PolicyEvaluationRequest
from app.services.approval_service import create_approval_request
from app.services.policy_service import evaluate_policy

logger = logging.getLogger("enterpriseai.actions")


def _row_to_action_record(row: tuple) -> ActionRecord:
    (
        action_id,
        scenario_id,
        decision_id,
        action_type,
        target_entity_id,
        payload,
        action_status,
        requires_approval,
        approved_by,
        created_at,
        executed_at,
        result,
        idempotency_key,
    ) = row

    return ActionRecord(
        action_id=str(action_id),
        scenario_id=str(scenario_id),
        decision_id=str(decision_id) if decision_id else None,
        action_type=str(action_type),
        target_entity_id=str(target_entity_id) if target_entity_id else None,
        payload=payload if isinstance(payload, dict) else {},
        status=str(action_status),
        requires_approval=bool(requires_approval),
        approved_by=str(approved_by) if approved_by else None,
        created_at=created_at.isoformat() if created_at else "",
        executed_at=executed_at.isoformat() if executed_at else None,
        result=result if isinstance(result, dict) else None,
        idempotency_key=str(idempotency_key),
    )


def _compute_simulation_state_transition(
    conn,
    action_type: str,
    target_entity_id: Optional[str],
    payload: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Capture real before-state from PostgreSQL and compute projected after-state and delta."""
    action_upper = action_type.upper()
    spend = float(payload.get("estimated_cost") or payload.get("spend") or 0.0)
    quantity = float(payload.get("quantity") or 0.0)
    item_id = payload.get("item_id") or target_entity_id

    # 1. Financial actions: query active budget before state
    if action_upper in {"CREATE_PURCHASE_ORDER", "ALLOCATE_BUDGET", "DISPATCH_PAYMENT"}:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT budget_id, available_budget_inr, committed_spend_inr
                FROM budgets
                WHERE status = 'ACTIVE'
                ORDER BY available_budget_inr DESC
                LIMIT 1;
                """
            )
            b_row = cur.fetchone()
        if b_row:
            b_id, avail, committed = b_row[0], float(b_row[1]), float(b_row[2]) if b_row[2] is not None else 0.0
            proj_avail = max(0.0, avail - spend)
            proj_committed = committed + spend
            before = {"budget_id": b_id, "available_budget_inr": avail, "committed_spend_inr": committed}
            after = {"budget_id": b_id, "available_budget_inr": proj_avail, "committed_spend_inr": proj_committed}
            diff = {
                "available_budget_inr": {"before": avail, "after": proj_avail, "delta": -spend},
                "committed_spend_inr": {"before": committed, "after": proj_committed, "delta": spend},
            }
            return before, after, diff

    # 2. Inventory actions: query inventory before state
    if action_upper in {"ALLOCATE_INVENTORY", "FULFILL_ORDER", "CHECK_STOCK"} and item_id:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(available_qty), 0), COALESCE(SUM(reserved_qty), 0) FROM inventory WHERE item_id = %s;",
                (item_id,),
            )
            i_row = cur.fetchone()
        avail = float(i_row[0]) if i_row else 0.0
        reserved = float(i_row[1]) if i_row else 0.0
        proj_avail = max(0.0, avail - quantity)
        proj_reserved = reserved + quantity
        before = {"item_id": item_id, "available_qty": avail, "reserved_qty": reserved}
        after = {"item_id": item_id, "available_qty": proj_avail, "reserved_qty": proj_reserved}
        diff = {
            "available_qty": {"before": avail, "after": proj_avail, "delta": -quantity},
            "reserved_qty": {"before": reserved, "after": proj_reserved, "delta": quantity},
        }
        return before, after, diff

    # 3. Maintenance actions: query maintenance_assets before state
    asset_id = payload.get("asset_id") or target_entity_id
    if action_upper in {"TRIGGER_EMERGENCY_MAINTENANCE", "OVERRIDE_MAINTENANCE_SCHEDULE", "SHUTDOWN_ASSET"} or (asset_id and asset_id.startswith("AST-")):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT asset_id, health_status, failure_risk_score FROM maintenance_assets WHERE asset_id = %s;",
                (asset_id,),
            )
            m_row = cur.fetchone()
        if m_row:
            a_id, h_status, risk = m_row[0], m_row[1], float(m_row[2]) if m_row[2] is not None else 0.0
            before = {"asset_id": a_id, "health_status": h_status, "failure_risk_score": risk}
            after = {"asset_id": a_id, "health_status": "MAINTENANCE_SCHEDULED", "failure_risk_score": 0.10}
            diff = {
                "health_status": {"before": h_status, "after": "MAINTENANCE_SCHEDULED"},
                "failure_risk_score": {"before": risk, "after": 0.10, "delta": round(0.10 - risk, 4)},
            }
            return before, after, diff

    # 4. Production stoppage actions
    if action_upper in {"PRODUCTION_STOP", "LINE_STOP", "SCHEDULE_OVERRIDE", "EMERGENCY_SHUTDOWN"}:
        line_id = payload.get("production_line_id") or target_entity_id or "LINE-01"
        before = {"production_line_id": line_id, "line_status": "RUNNING"}
        after = {"production_line_id": line_id, "line_status": "STOPPED"}
        diff = {"line_status": {"before": "RUNNING", "after": "STOPPED"}}
        return before, after, diff

    # 5. Quality / safety override actions
    if action_upper in {"QUALITY_RELEASE_OVERRIDE", "RELEASE_QUALITY_HOLD", "SAFETY_HOLD_OVERRIDE", "OVERRIDE_SAFETY_ALERT"}:
        entity = target_entity_id or item_id or "GENERAL"
        before = {"entity_id": entity, "hold_status": "ACTIVE_HOLD"}
        after = {"entity_id": entity, "hold_status": "OVERRIDDEN_BY_APPROVAL"}
        diff = {"hold_status": {"before": "ACTIVE_HOLD", "after": "OVERRIDDEN_BY_APPROVAL"}}
        return before, after, diff

    # 6. Default fallback operational transition
    entity = target_entity_id or item_id or "OPERATIONAL_STATE"
    before = {"entity_id": entity, "status": "PENDING_EXECUTION"}
    after = {"entity_id": entity, "status": "SIMULATED_APPLIED"}
    diff = {"status": {"before": "PENDING_EXECUTION", "after": "SIMULATED_APPLIED"}}
    return before, after, diff


class SafeSimulationAdapter:
    """Safe simulation execution adapter for consequential supply chain actions."""

    @staticmethod
    def execute(
        action_type: str,
        payload: Dict[str, Any],
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        diff: Optional[Dict[str, Any]] = None,
        actor: str = "SystemExecutor",
        approver: Optional[str] = None,
        policy_result: Optional[str] = "PASS",
    ) -> Dict[str, Any]:
        """Simulate action execution with deterministic outcome, state transitions, and audit metadata."""
        ref_id = f"SIM-{action_type[:4]}-{uuid.uuid4().hex[:6].upper()}"
        b_state = before_state or {"status": "PENDING_EXECUTION"}
        a_state = after_state or {"status": "SIMULATED_APPLIED"}
        s_diff = diff or {"status": {"before": "PENDING_EXECUTION", "after": "SIMULATED_APPLIED"}}
        return {
            "execution_mode": "SIMULATION",
            "adapter": "SafeSimulationAdapter",
            "confirmed": True,
            "reference_number": ref_id,
            "action_type": action_type,
            "target_entity": payload.get("item_id") or payload.get("supplier_id") or payload.get("order_id"),
            "actor": actor,
            "approver": approver,
            "policy_result": policy_result,
            "before_state": b_state,
            "after_state": a_state,
            "diff": s_diff,
            "details": f"Simulated {action_type} executed safely without live side-effects.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def propose_action(conn, req: ActionProposeRequest) -> ActionRecord:
    """Propose an action into action_queue, gating it through deterministic policy checks."""
    try:
        val_scenario_uuid = uuid.UUID(req.scenario_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario_id UUID: '{req.scenario_id}'",
        )

    # Check idempotency
    idemp_key = req.idempotency_key or f"ACT-{uuid.uuid4()}"
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                action_id, scenario_id, decision_id, action_type, target_entity_id,
                payload, status, requires_approval, approved_by, created_at,
                executed_at, result, idempotency_key
            FROM action_queue
            WHERE idempotency_key = %s;
            """,
            (idemp_key,),
        )
        existing = cur.fetchone()
        if existing:
            return _row_to_action_record(existing)

        action_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        sanitized_payload = sanitize_dict(req.payload)

        # 1. Gate: Deterministic Policy Evaluation
        eval_req = PolicyEvaluationRequest(
            action_type=req.action_type,
            target_entity_id=req.target_entity_id,
            payload=req.payload,
            decision_id=req.decision_id,
            action_id=str(action_id),
            scenario_id=req.scenario_id,
        )
        eval_result = evaluate_policy(conn, eval_req)

        if eval_result.overall_result == "FAIL":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action rejected by policy: {eval_result.rejection_reason}",
            )

        requires_approval = eval_result.requires_approval
        initial_status = "PROPOSED" if requires_approval else "APPROVED"

        # If a decision_id is provided, verify or generate placeholder decision if needed
        decision_uuid = None
        if req.decision_id:
            try:
                decision_uuid = uuid.UUID(req.decision_id)
            except ValueError:
                pass

        if not decision_uuid:
            # Check if there is an existing decision for this scenario
            cur.execute(
                "SELECT decision_id FROM decisions WHERE scenario_id = %s LIMIT 1;",
                (str(val_scenario_uuid),),
            )
            d_row = cur.fetchone()
            if d_row:
                decision_uuid = d_row[0]
            else:
                # Create parent decision record
                decision_uuid = uuid.uuid4()
                cur.execute(
                    """
                    INSERT INTO decisions (
                        decision_id, scenario_id, workflow_run_id, decision_at,
                        supervisor_summary, decision_code, recommended_action
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        str(decision_uuid),
                        str(val_scenario_uuid),
                        str(val_scenario_uuid),
                        now,
                        f"Automated decision for proposed action {req.action_type}",
                        "DEC-PROPOSED",
                        json.dumps({"action_type": req.action_type}),
                    ),
                )

        cur.execute(
            """
            INSERT INTO action_queue (
                action_id, scenario_id, decision_id, action_type, target_entity_id,
                payload, status, requires_approval, created_at, idempotency_key
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING
                action_id, scenario_id, decision_id, action_type, target_entity_id,
                payload, status, requires_approval, approved_by, created_at,
                executed_at, result, idempotency_key;
            """,
            (
                str(action_id),
                str(val_scenario_uuid),
                str(decision_uuid),
                req.action_type.upper(),
                req.target_entity_id,
                json.dumps(sanitized_payload),
                initial_status,
                requires_approval,
                now,
                idemp_key,
            ),
        )
        row = cur.fetchone()

        # Link policy evaluation records to the created action_id and decision_id
        if eval_result.policy_eval_ids:
            cur.execute(
                """
                UPDATE policy_evaluations
                SET action_id = %s, decision_id = %s
                WHERE policy_eval_id::text = ANY(%s);
                """,
                (str(action_id), str(decision_uuid), eval_result.policy_eval_ids),
            )

        # If approval is required, create approval request record in approval_requests table
        if requires_approval:
            create_approval_request(
                conn,
                required_domain=eval_result.approval_domain or "FINANCE",
                action_id=str(action_id),
                decision_id=str(decision_uuid),
                scenario_id=str(val_scenario_uuid),
            )

        conn.commit()

        default_event_manager.publish(
            event_type=EventType.ACTION_PROPOSED.value,
            channel=EventChannel.ACTIONS.value,
            entity_id=str(action_id),
            entity_type="ACTION",
            scenario_id=str(val_scenario_uuid),
            payload={
                "action_id": str(action_id),
                "action_type": req.action_type.upper(),
                "target_entity_id": req.target_entity_id,
                "status": initial_status,
                "requires_approval": requires_approval,
                "created_at": now.isoformat(),
            },
        )

        return _row_to_action_record(row)


def execute_action(
    conn,
    action_id: str,
    caller_id: str = "SystemExecutor",
) -> ActionRecord:
    """Execute an action after validating policy gates, approval status, and preconditions."""
    try:
        val_action_uuid = uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_id UUID: '{action_id}'",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                action_id, scenario_id, decision_id, action_type, target_entity_id,
                payload, status, requires_approval, approved_by, created_at,
                executed_at, result, idempotency_key
            FROM action_queue
            WHERE action_id = %s
            FOR UPDATE;
            """,
            (str(val_action_uuid),),
        )
        current = cur.fetchone()
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Action '{action_id}' not found.",
            )

        curr_status = current[6]
        requires_approval = current[7]

        # 1. Gate: Idempotency (already completed)
        if curr_status == "SUCCEEDED":
            logger.info("Action '%s' already executed; returning existing result idempotently.", action_id)
            return _row_to_action_record(current)

        # 2. Gate: Rejection block
        if curr_status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action '{action_id}' was rejected and cannot be executed.",
            )

        # 3. Gate: Approval check
        if requires_approval and curr_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action '{action_id}' requires human approval before execution (status: {curr_status}).",
            )

        # 4. Gate: Precondition check immediately before execution
        action_type = current[3]
        payload = current[5] or {}
        eval_req = PolicyEvaluationRequest(
            action_type=action_type,
            target_entity_id=current[4],
            payload=payload,
            decision_id=current[2],
            scenario_id=current[1],
        )
        precheck = evaluate_policy(conn, eval_req)
        if precheck.overall_result == "FAIL":
            # Record failure in execution results
            exec_id = uuid.uuid4()
            now = datetime.now(timezone.utc)
            err_msg = f"Precondition gate failed: {precheck.rejection_reason}"
            cur.execute(
                """
                INSERT INTO action_execution_results (execution_id, action_id, attempted_at, status, error_message)
                VALUES (%s, %s, %s, 'FAILED', %s);
                """,
                (str(exec_id), str(val_action_uuid), now, err_msg),
            )
            cur.execute(
                "UPDATE action_queue SET status = 'FAILED' WHERE action_id = %s;",
                (str(val_action_uuid),),
            )
            conn.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg,
            )

        # 5. Execute action via Safe Simulation Adapter with state transition tracking
        now = datetime.now(timezone.utc)
        cur.execute(
            "UPDATE action_queue SET status = 'EXECUTING' WHERE action_id = %s;",
            (str(val_action_uuid),),
        )

        before_state, after_state, diff = _compute_simulation_state_transition(
            conn, action_type, current[4], payload
        )

        sim_result = SafeSimulationAdapter.execute(
            action_type=action_type,
            payload=payload,
            before_state=before_state,
            after_state=after_state,
            diff=diff,
            actor=caller_id,
            approver=current[8],
            policy_result=precheck.overall_result,
        )
        exec_id = uuid.uuid4()

        # Record execution attempt in action_execution_results
        cur.execute(
            """
            INSERT INTO action_execution_results (
                execution_id, action_id, attempted_at, status, result
            )
            VALUES (%s, %s, %s, 'SUCCEEDED', %s);
            """,
            (str(exec_id), str(val_action_uuid), now, json.dumps(sim_result)),
        )

        # Record audit event in event_log
        event_id = str(uuid.uuid4())
        try:
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
                    event_id, now, "ACTION_EXECUTED", "ACTION", str(val_action_uuid),
                    str(current[1]), str(current[1]),
                    "USER" if caller_id != "GovernedOrchestrator" else "SYSTEM", caller_id, "SUCCEEDED",
                    "SAFE_SIMULATION_EXECUTION",
                    json.dumps([{
                        "action_id": str(val_action_uuid),
                        "action_type": action_type,
                        "policy_result": precheck.overall_result,
                        "actor": caller_id,
                        "approver": current[8],
                        "before_state": before_state,
                        "after_state": after_state,
                        "diff": diff,
                    }]),
                    "", "ACTION_SERVICE",
                ),
            )
        except Exception as a_exc:
            logger.warning("Could not log action execution audit event: %s", a_exc)

        # Update action_queue to SUCCEEDED
        cur.execute(
            """
            UPDATE action_queue
            SET
                status = 'SUCCEEDED',
                executed_at = %s,
                result = %s
            WHERE action_id = %s
            RETURNING
                action_id, scenario_id, decision_id, action_type, target_entity_id,
                payload, status, requires_approval, approved_by, created_at,
                executed_at, result, idempotency_key;
            """,
            (now, json.dumps(sim_result), str(val_action_uuid)),
        )
        updated = cur.fetchone()
        conn.commit()

        default_event_manager.publish(
            event_type=EventType.ACTION_EXECUTED.value,
            channel=EventChannel.ACTIONS.value,
            entity_id=str(val_action_uuid),
            entity_type="ACTION",
            scenario_id=str(current[1]),
            payload={
                "action_id": str(val_action_uuid),
                "action_type": action_type,
                "status": "SUCCEEDED",
                "actor": caller_id,
                "approver": current[8],
                "before_state": before_state,
                "after_state": after_state,
                "diff": diff,
                "executed_at": now.isoformat(),
            },
        )

        return _row_to_action_record(updated)


def get_action(conn, action_id: str) -> Optional[ActionDetailResponse]:
    """Retrieve action record and complete execution attempt history."""
    try:
        val_uuid = uuid.UUID(action_id)
    except ValueError:
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                action_id, scenario_id, decision_id, action_type, target_entity_id,
                payload, status, requires_approval, approved_by, created_at,
                executed_at, result, idempotency_key
            FROM action_queue
            WHERE action_id = %s;
            """,
            (str(val_uuid),),
        )
        row = cur.fetchone()
        if not row:
            return None

        action_rec = _row_to_action_record(row)

        cur.execute(
            """
            SELECT execution_id, action_id, attempted_at, status, result, error_message
            FROM action_execution_results
            WHERE action_id = %s
            ORDER BY attempted_at ASC;
            """,
            (str(val_uuid),),
        )
        exec_rows = cur.fetchall()
        history = [
            ActionExecutionResultRecord(
                execution_id=str(r[0]),
                action_id=str(r[1]),
                attempted_at=r[2].isoformat() if r[2] else "",
                status=str(r[3]),
                result=r[4] if isinstance(r[4], dict) else None,
                error_message=str(r[5]) if r[5] else None,
            )
            for r in exec_rows
        ]

        return ActionDetailResponse(action=action_rec, execution_history=history)


def list_actions(
    conn,
    scenario_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ActionRecord], int]:
    """List actions with filtering and pagination."""
    clauses: list[str] = []
    params: list = []

    if scenario_id:
        clauses.append("scenario_id = %s")
        params.append(scenario_id)

    if status_filter:
        clauses.append("status = %s")
        params.append(status_filter.upper().strip())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            action_id, scenario_id, decision_id, action_type, target_entity_id,
            payload, status, requires_approval, approved_by, created_at,
            executed_at, result, idempotency_key,
            COUNT(*) OVER() AS total_count
        FROM action_queue
        {where_sql}
        ORDER BY created_at DESC, action_id DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        return [], 0

    total = rows[0][13]
    records = [_row_to_action_record(r[:13]) for r in rows]
    return records, total
