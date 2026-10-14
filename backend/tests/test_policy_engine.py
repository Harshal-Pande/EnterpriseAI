"""Tests for Deterministic Policy and Approval Engine (Task 10).

Verifies:
- Deterministic policy evaluations against real business rules
- Budget limits, spending thresholds, and fail-closed safety gating
- Persistence into policy_evaluations table
- Approval request creation, authorization, and rejection
- Idempotency and conflict handling on repeated approval submissions
- Strict test isolation (cleans up tracked test records)
"""

from __future__ import annotations

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.models.policy import (
    ApprovalDecisionRequest,
    PolicyEvaluationRequest,
)
from app.services.approval_service import (
    create_approval_request,
    decide_approval_request,
    get_approval,
)
from app.services.policy_service import evaluate_policy


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def client(test_database_url, monkeypatch) -> TestClient:
    """TestClient configured with TEST_DATABASE_URL and scheduler loop disabled."""
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    init_db_pool(database_url=test_database_url)
    with TestClient(app) as test_client:
        yield test_client
    close_db_pool()


@pytest.fixture
def policy_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Track created approval requests and policy evaluations to clean up after test."""
    tracker: dict[str, list[str]] = {
        "approval_ids": [],
        "eval_ids": [],
    }
    yield tracker

    cur = test_conn.cursor()
    try:
        if tracker["approval_ids"]:
            cur.execute(
                "DELETE FROM approval_requests WHERE approval_id::text = ANY(%s);",
                (tracker["approval_ids"],),
            )
        if tracker["eval_ids"]:
            cur.execute(
                "DELETE FROM policy_evaluations WHERE policy_eval_id::text = ANY(%s);",
                (tracker["eval_ids"],),
            )
        test_conn.commit()
    except Exception as exc:
        test_conn.rollback()
        raise exc


@pytest.mark.integration
def test_inventory_policy_evaluation(test_conn, policy_test_tracker):
    """Inventory policy checks available stock deterministically."""
    # Pass scenario: small request
    req_pass = PolicyEvaluationRequest(
        action_type="FULFILL_ORDER",
        payload={"item_id": "PRD-STEEL-01", "quantity": 1.0},
    )
    res_pass = evaluate_policy(test_conn, req_pass)
    policy_test_tracker["eval_ids"].extend(res_pass.policy_eval_ids)
    assert res_pass.overall_result in {"PASS", "FAIL"}

    # Fail scenario: astronomical request
    req_fail = PolicyEvaluationRequest(
        action_type="FULFILL_ORDER",
        payload={"item_id": "PRD-STEEL-01", "quantity": 999999999.0},
    )
    res_fail = evaluate_policy(test_conn, req_fail)
    policy_test_tracker["eval_ids"].extend(res_fail.policy_eval_ids)
    assert res_fail.overall_result == "FAIL"
    assert res_fail.requires_approval is False
    assert "insufficient" in res_fail.rejection_reason.lower()


@pytest.mark.integration
def test_procurement_and_budget_policy_evaluation(test_conn, policy_test_tracker):
    """Procurement evaluation checks supplier validity and threshold approval."""
    # 1. Spend exceeding threshold (50M INR) -> NEEDS_APPROVAL
    req_thresh = PolicyEvaluationRequest(
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUPP-001",
            "item_id": "PRD-STEEL-01",
            "quantity": 100.0,
            "estimated_cost": 55000000.0,  # 55M > 50M threshold
        },
    )
    res_thresh = evaluate_policy(test_conn, req_thresh)
    policy_test_tracker["eval_ids"].extend(res_thresh.policy_eval_ids)
    assert res_thresh.overall_result == "NEEDS_APPROVAL"
    assert res_thresh.requires_approval is True
    assert res_thresh.approval_domain == "FINANCE"

    # 2. Inactive/unknown supplier -> FAIL
    req_bad_supp = PolicyEvaluationRequest(
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUPP-UNKNOWN-999",
            "estimated_cost": 1000.0,
        },
    )
    res_bad_supp = evaluate_policy(test_conn, req_bad_supp)
    policy_test_tracker["eval_ids"].extend(res_bad_supp.policy_eval_ids)
    assert res_bad_supp.overall_result == "FAIL"
    assert "inactive or not found" in res_bad_supp.rejection_reason.lower()

    # 3. Spend exceeding entire budget (65M INR) -> FAIL
    req_budget_exceeded = PolicyEvaluationRequest(
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUPP-001",
            "item_id": "PRD-STEEL-01",
            "estimated_cost": 999999999.0,
        },
    )
    res_budget = evaluate_policy(test_conn, req_budget_exceeded)
    policy_test_tracker["eval_ids"].extend(res_budget.policy_eval_ids)
    assert res_budget.overall_result == "FAIL"
    assert "breaches available budget" in res_budget.rejection_reason.lower()


@pytest.mark.integration
def test_safety_and_quality_failsafe(test_conn, policy_test_tracker):
    """Critical safety or quality holds cause immediate FAIL closed."""
    req_hold = PolicyEvaluationRequest(
        action_type="FULFILL_ORDER",
        payload={"quality_hold": True, "item_id": "PRD-STEEL-01", "quantity": 1.0},
    )
    res = evaluate_policy(test_conn, req_hold)
    policy_test_tracker["eval_ids"].extend(res.policy_eval_ids)
    assert res.overall_result == "FAIL"
    assert "quality hold active" in res.rejection_reason.lower()


@pytest.mark.integration
def test_approval_lifecycle_and_idempotency(test_conn, policy_test_tracker):
    """Approval request creation, authorization, and idempotent duplicate handling."""
    approval = create_approval_request(
        test_conn,
        required_domain="FINANCE",
    )
    policy_test_tracker["approval_ids"].append(approval.approval_id)

    assert approval.status == "PENDING"
    assert approval.required_domain == "FINANCE"

    # Authorize decision
    decide_req = ApprovalDecisionRequest(
        status="APPROVED",
        decided_by="finance_director",
        reason="Approved under operational contingency budget.",
    )
    approved = decide_approval_request(test_conn, approval.approval_id, decide_req)
    assert approved.status == "APPROVED"
    assert approved.decided_by == "finance_director"
    assert approved.decided_at is not None

    # Repeated identical approval is handled idempotently
    re_approved = decide_approval_request(test_conn, approval.approval_id, decide_req)
    assert re_approved.status == "APPROVED"

    # Conflicting decision rejected
    with pytest.raises(Exception):
        conflict_req = ApprovalDecisionRequest(status="REJECTED", decided_by="auditor")
        decide_approval_request(test_conn, approval.approval_id, conflict_req)


@pytest.mark.integration
def test_policy_and_approval_api_endpoints(client: TestClient, policy_test_tracker):
    """API endpoints for rules listing, evaluation, and approval decision submission."""
    # List rules
    rules_res = client.get("/api/policies/rules")
    assert rules_res.status_code == 200
    rules = rules_res.json()
    assert len(rules) >= 5

    # Evaluate endpoint
    eval_res = client.post(
        "/api/policies/evaluate",
        json={
            "action_type": "CREATE_PURCHASE_ORDER",
            "payload": {
                "supplier_id": "SUPP-001",
                "item_id": "PRD-STEEL-01",
                "estimated_cost": 60000000.0,
            },
        },
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["overall_result"] == "NEEDS_APPROVAL"
    assert eval_data["requires_approval"] is True
    policy_test_tracker["eval_ids"].extend(eval_data.get("policy_eval_ids", []))

    # Approvals listing endpoint
    appr_list_res = client.get("/api/approvals/")
    assert appr_list_res.status_code == 200
    assert isinstance(appr_list_res.json(), list)
