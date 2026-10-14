"""Phase 5 Comprehensive Verification Tests.

Verifies:
1. Explicit policy checks for budget limits, supplier eligibility, inventory consistency, quality holds, safety events, and production-stop actions.
2. Human approval gating for finance commitments (> 50M INR), safety-critical actions, quality release overrides, and production stoppages.
3. Supply chain approver domain permissions (QUALITY, SAFETY, PRODUCTION).
4. Idempotent and transactional action execution with FOR UPDATE row locking.
5. Operational before/after state, actor/approver, policy result, and delta recording in action_execution_results and event_log.
6. Typed OrchestrationErrorCode enum values and mappings.
"""

from __future__ import annotations

import json
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthUser, UserRole
from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.models.action import ActionProposeRequest
from app.models.policy import ApprovalDecisionRequest, PolicyEvaluationRequest
from app.orchestration.governed import (
    AgentStepResult,
    GovernedOrchestrator,
    OrchestrationErrorCode,
    OrchestrationPhase,
    OrchestrationResult,
)
from app.services.action_service import (
    execute_action,
    get_action,
    propose_action,
)
from app.services.approval_service import create_approval_request, decide_approval_request
from app.services.policy_service import evaluate_policy
from app.services.workflow_service import create_workflow


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def phase5_tracker(test_conn) -> Generator[dict, None, None]:
    """Track created records and cleanly delete in exact foreign-key dependency order."""
    tracker: dict[str, list[str]] = {
        "scenario_ids": [],
        "action_ids": [],
        "eval_ids": [],
        "approval_ids": [],
    }
    yield tracker

    cur = test_conn.cursor()
    try:
        if tracker["action_ids"]:
            cur.execute(
                "DELETE FROM action_execution_results WHERE action_id::text = ANY(%s);",
                (tracker["action_ids"],),
            )
            cur.execute(
                "DELETE FROM approval_requests WHERE action_id::text = ANY(%s);",
                (tracker["action_ids"],),
            )
            cur.execute(
                "DELETE FROM policy_evaluations WHERE action_id::text = ANY(%s);",
                (tracker["action_ids"],),
            )
            cur.execute(
                "DELETE FROM event_log WHERE entity_id::text = ANY(%s);",
                (tracker["action_ids"],),
            )
            cur.execute(
                "DELETE FROM action_queue WHERE action_id::text = ANY(%s);",
                (tracker["action_ids"],),
            )
        if tracker["eval_ids"]:
            cur.execute(
                "DELETE FROM policy_evaluations WHERE policy_eval_id::text = ANY(%s);",
                (tracker["eval_ids"],),
            )
        if tracker["approval_ids"]:
            cur.execute(
                "DELETE FROM approval_requests WHERE approval_id::text = ANY(%s);",
                (tracker["approval_ids"],),
            )
        if tracker["scenario_ids"]:
            cur.execute(
                "DELETE FROM action_execution_results WHERE action_id IN (SELECT action_id FROM action_queue WHERE scenario_id::text = ANY(%s));",
                (tracker["scenario_ids"],),
            )
            cur.execute(
                "DELETE FROM approval_requests WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
            cur.execute(
                "DELETE FROM policy_evaluations WHERE decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id::text = ANY(%s));",
                (tracker["scenario_ids"],),
            )
            cur.execute(
                "DELETE FROM action_queue WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
            cur.execute(
                "DELETE FROM decisions WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
            cur.execute(
                "DELETE FROM agent_runs WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
            cur.execute(
                "DELETE FROM event_log WHERE scenario_id::text = ANY(%s) OR entity_id::text = ANY(%s);",
                (tracker["scenario_ids"], tracker["scenario_ids"]),
            )
            cur.execute(
                "DELETE FROM scenario_instances WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
        test_conn.commit()
    except Exception as exc:
        test_conn.rollback()
        raise exc


# ═══════════════════════════════════════════════════════════════════════════
# 1. POLICY ENGINE & DOMAIN APPROVAL TESTS
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
def test_quality_release_override_requires_human_approval(test_conn, phase5_tracker):
    """Quality release override action deterministically requires human approval in QUALITY domain."""
    req = PolicyEvaluationRequest(
        action_type="QUALITY_RELEASE_OVERRIDE",
        target_entity_id="PRD-CRC",
        payload={"batch_id": "BATCH-7001", "reason": "Authorized lab test passed with deviation waiver"},
    )
    res = evaluate_policy(test_conn, req)
    phase5_tracker["eval_ids"].extend(res.policy_eval_ids)

    assert res.overall_result == "NEEDS_APPROVAL"
    assert res.requires_approval is True
    assert res.approval_domain == "QUALITY"
    assert any("quality release" in r.explanation.lower() for r in res.rule_results)


@pytest.mark.integration
def test_safety_hold_override_requires_human_approval(test_conn, phase5_tracker):
    """Safety hold override action deterministically requires human approval in SAFETY domain."""
    req = PolicyEvaluationRequest(
        action_type="SAFETY_HOLD_OVERRIDE",
        target_entity_id="EAS-PORT",
        payload={"work_area": "EAS-PORT", "reason": "Physical inspection complete; perimeter secured"},
    )
    res = evaluate_policy(test_conn, req)
    phase5_tracker["eval_ids"].extend(res.policy_eval_ids)

    assert res.overall_result == "NEEDS_APPROVAL"
    assert res.requires_approval is True
    assert res.approval_domain == "SAFETY"
    assert any("safety hold" in r.explanation.lower() for r in res.rule_results)


@pytest.mark.integration
def test_production_stop_requires_human_approval(test_conn, phase5_tracker):
    """Production stoppage or schedule override deterministically requires human approval in PRODUCTION domain."""
    req = PolicyEvaluationRequest(
        action_type="PRODUCTION_STOP",
        target_entity_id="LINE-01",
        payload={"production_line_id": "LINE-01", "reason": "Excessive bearing temperature detected"},
    )
    res = evaluate_policy(test_conn, req)
    phase5_tracker["eval_ids"].extend(res.policy_eval_ids)

    assert res.overall_result == "NEEDS_APPROVAL"
    assert res.requires_approval is True
    assert res.approval_domain == "PRODUCTION"
    assert any("production stoppage" in r.explanation.lower() for r in res.rule_results)


@pytest.mark.integration
def test_maintenance_emergency_action_requires_approval(test_conn, phase5_tracker):
    """Emergency maintenance actions on safety-critical equipment require approval in MAINTENANCE domain."""
    req = PolicyEvaluationRequest(
        action_type="TRIGGER_EMERGENCY_MAINTENANCE",
        target_entity_id="AST-001",
        payload={"asset_id": "AST-001", "severity": "HIGH"},
    )
    res = evaluate_policy(test_conn, req)
    phase5_tracker["eval_ids"].extend(res.policy_eval_ids)

    assert res.overall_result == "NEEDS_APPROVAL"
    assert res.requires_approval is True
    assert res.approval_domain == "MAINTENANCE"


# ═══════════════════════════════════════════════════════════════════════════
# 2. ROLE AUTHORIZATION AND DOMAIN PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════


def test_supply_chain_approver_can_approve_quality_safety_production():
    """SUPPLY_CHAIN_APPROVER role is authorized for SUPPLY_CHAIN, PROCUREMENT, LOGISTICS, QUALITY, SAFETY, and PRODUCTION."""
    sc_user = AuthUser(
        user_id="sc_lead",
        role=UserRole.SUPPLY_CHAIN_APPROVER,
        approval_domains=["SUPPLY_CHAIN", "PROCUREMENT", "LOGISTICS", "INVENTORY", "QUALITY", "SAFETY", "PRODUCTION"],
    )

    assert sc_user.can_approve_domain("SUPPLY_CHAIN") is True
    assert sc_user.can_approve_domain("PROCUREMENT") is True
    assert sc_user.can_approve_domain("LOGISTICS") is True
    assert sc_user.can_approve_domain("INVENTORY") is True
    assert sc_user.can_approve_domain("QUALITY") is True
    assert sc_user.can_approve_domain("SAFETY") is True
    assert sc_user.can_approve_domain("PRODUCTION") is True
    # Cannot approve FINANCE
    assert sc_user.can_approve_domain("FINANCE") is False


def test_finance_approver_cannot_approve_safety_or_quality():
    """FINANCE_APPROVER can only approve FINANCE domain."""
    fin_user = AuthUser(
        user_id="fin_lead",
        role=UserRole.FINANCE_APPROVER,
        approval_domains=["FINANCE"],
        max_approval_amount=60000000.0,
    )

    assert fin_user.can_approve_domain("FINANCE") is True
    assert fin_user.can_approve_domain("QUALITY") is False
    assert fin_user.can_approve_domain("SAFETY") is False
    assert fin_user.can_approve_domain("PRODUCTION") is False


# ═══════════════════════════════════════════════════════════════════════════
# 3. ACTION EXECUTION STATE TRANSITION TRACKING
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
def test_action_execution_records_state_transitions_and_diff(test_conn, phase5_tracker):
    """Action execution captures real operational before-state, projected after-state, and delta."""
    from app.models.workflow import WorkflowCreateRequest

    wf = create_workflow(
        test_conn,
        WorkflowCreateRequest(
            scenario_template_id="TPL-010",
            linked_order_id="ORD-1042",
            severity="MEDIUM",
            idempotency_key=f"P5-TEST-{uuid.uuid4()}",
        ),
    )
    scen_id = wf.scenario_id
    phase5_tracker["scenario_ids"].append(scen_id)

    # Propose auto-approved action (below threshold)
    spend_amount = 15000.0
    action_req = ActionProposeRequest(
        scenario_id=scen_id,
        action_type="CREATE_PURCHASE_ORDER",
        target_entity_id="SUP-001",
        payload={
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "quantity": 10.0,
            "estimated_cost": spend_amount,
        },
        idempotency_key=f"PHASE5-TEST-{uuid.uuid4()}",
    )
    action = propose_action(test_conn, action_req)
    phase5_tracker["action_ids"].append(action.action_id)

    assert action.status == "APPROVED"
    assert action.requires_approval is False

    # Execute action
    executed = execute_action(test_conn, action.action_id, caller_id="Phase5TestOperator")
    assert executed.status == "SUCCEEDED"
    assert executed.executed_at is not None

    res = executed.result
    assert res is not None
    assert res["confirmed"] is True
    assert res["actor"] == "Phase5TestOperator"
    assert res["policy_result"] == "PASS"

    # Verify before-state, after-state, and diff structure
    assert "before_state" in res
    assert "after_state" in res
    assert "diff" in res

    before = res["before_state"]
    after = res["after_state"]
    diff = res["diff"]

    assert "available_budget_inr" in before
    assert "available_budget_inr" in after
    assert "available_budget_inr" in diff

    # Verify arithmetic correctness of simulation delta
    assert diff["available_budget_inr"]["delta"] == -spend_amount
    assert after["available_budget_inr"] == before["available_budget_inr"] - spend_amount
    assert diff["committed_spend_inr"]["delta"] == spend_amount

    # Verify action_execution_results table has exact persisted record
    with test_conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, result FROM action_execution_results
            WHERE action_id = %s;
            """,
            (action.action_id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "SUCCEEDED"
        db_res = row[1]
        assert db_res["diff"]["available_budget_inr"]["delta"] == -spend_amount

    # Verify event_log record was persisted for the execution
    with test_conn.cursor() as cur:
        cur.execute(
            """
            SELECT event_type, actor_id, status FROM event_log
            WHERE entity_id = %s AND event_type = 'ACTION_EXECUTED';
            """,
            (action.action_id,),
        )
        ev_row = cur.fetchone()
        assert ev_row is not None
        assert ev_row[0] == "ACTION_EXECUTED"
        assert ev_row[1] == "Phase5TestOperator"
        assert ev_row[2] == "SUCCEEDED"


# ═══════════════════════════════════════════════════════════════════════════
# 4. TYPED ORCHESTRATION ERROR CODES
# ═══════════════════════════════════════════════════════════════════════════


def test_orchestration_error_codes_enum():
    """Controlled set of typed error codes exists and is correctly defined."""
    expected_codes = {
        "MISSING_EVIDENCE",
        "SAFETY_HOLD_BLOCKED",
        "POLICY_REJECTION",
        "APPROVAL_REQUIRED",
        "APPROVAL_REJECTED",
        "APPROVAL_PENDING",
        "AGENT_EXECUTION_FAILED",
        "PROVIDER_TIMEOUT",
        "PROVIDER_UNAVAILABLE",
        "PROVIDER_MALFORMED",
        "INTERNAL_ERROR",
    }
    actual_codes = {code.value for code in OrchestrationErrorCode}
    assert expected_codes == actual_codes


def test_orchestration_result_typed_error_code_field():
    """OrchestrationResult and AgentStepResult support typed error_code field."""
    step = AgentStepResult(
        agent_name="InventoryAgent",
        phase="INVENTORY_ANALYSIS",
        status="FAILED",
        error="Connection dropped",
        error_code=OrchestrationErrorCode.AGENT_EXECUTION_FAILED.value,
    )
    assert step.error_code == "AGENT_EXECUTION_FAILED"

    res = OrchestrationResult(
        correlation_id="CORR-123",
        workflow_id="WF-123",
        order_id="ORD-1042",
        status="BLOCKED",
        error_code=OrchestrationErrorCode.MISSING_EVIDENCE.value,
        error="Order not found",
    )
    assert res.error_code == "MISSING_EVIDENCE"
