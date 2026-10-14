"""Tests for Controlled Action Execution (Task 11).

Verifies:
- Action proposal with policy gating and approval requirement detection
- Strict execution gates (blocking unapproved actions and rejected actions)
- Safe simulation adapter execution
- Recording attempts and results into action_execution_results
- Idempotent execution (duplicate calls do not repeat side effects)
- Strict test isolation (cleans up tracked test records)
"""

from __future__ import annotations

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.models.action import ActionProposeRequest
from app.models.policy import ApprovalDecisionRequest
from app.services.action_service import (
    execute_action,
    get_action,
    propose_action,
)
from app.services.approval_service import decide_approval_request


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
def action_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Track created actions, approvals, and scenarios to clean up after test."""
    tracker: dict[str, list[str]] = {
        "action_ids": [],
        "approval_ids": [],
        "scenario_ids": [],
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
                "DELETE FROM policy_evaluations WHERE action_id IN (SELECT action_id FROM action_queue WHERE scenario_id::text = ANY(%s)) OR decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id::text = ANY(%s));",
                (tracker["scenario_ids"], tracker["scenario_ids"]),
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
                "DELETE FROM agent_findings WHERE scenario_id::text = ANY(%s) OR agent_run_id IN (SELECT agent_run_id FROM agent_runs WHERE scenario_id::text = ANY(%s));",
                (tracker["scenario_ids"], tracker["scenario_ids"]),
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


@pytest.fixture
def parent_scenario(client: TestClient, action_test_tracker) -> str:
    """Create parent scenario instance for actions."""
    res = client.post(
        "/api/workflow/",
        json={"scenario_template_id": "TPL-010", "linked_order_id": "ORD-ACT-TEST"},
    )
    assert res.status_code == 201
    sid = res.json()["scenario_id"]
    action_test_tracker["scenario_ids"].append(sid)
    return sid


@pytest.mark.integration
def test_propose_auto_approved_action(test_conn, parent_scenario: str, action_test_tracker):
    """Proposing action within limits is auto-approved without requiring manual approval."""
    req = ActionProposeRequest(
        scenario_id=parent_scenario,
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "quantity": 50.0,
            "estimated_cost": 25000.0,  # Below threshold
        },
    )
    action = propose_action(test_conn, req)
    action_test_tracker["action_ids"].append(action.action_id)

    assert action.status == "APPROVED"
    assert action.requires_approval is False


@pytest.mark.integration
def test_propose_action_requiring_approval_is_blocked_from_execution(
    test_conn, parent_scenario: str, action_test_tracker
):
    """Action exceeding threshold requires approval and is strictly blocked from execution."""
    req = ActionProposeRequest(
        scenario_id=parent_scenario,
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "quantity": 100.0,
            "estimated_cost": 55000000.0,  # 55M > 50M threshold
        },
    )
    action = propose_action(test_conn, req)
    action_test_tracker["action_ids"].append(action.action_id)

    assert action.status == "PROPOSED"
    assert action.requires_approval is True

    # Gate: Attempting execution while unapproved must fail
    with pytest.raises(Exception) as exc:
        execute_action(test_conn, action.action_id)
    assert "requires human approval" in str(exc.value).lower()


@pytest.mark.integration
def test_approved_action_executes_successfully_and_idempotently(
    test_conn, parent_scenario: str, action_test_tracker
):
    """Authorizing an approval allows execution; duplicate execution is idempotent."""
    req = ActionProposeRequest(
        scenario_id=parent_scenario,
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "quantity": 100.0,
            "estimated_cost": 55000000.0,
        },
    )
    action = propose_action(test_conn, req)
    action_test_tracker["action_ids"].append(action.action_id)

    # Find the created approval request
    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT approval_id FROM approval_requests WHERE action_id = %s;",
            (action.action_id,),
        )
        approval_id = cur.fetchone()[0]

    # Authorize approval
    decide_approval_request(
        test_conn,
        str(approval_id),
        ApprovalDecisionRequest(status="APPROVED", decided_by="supply_chain_head"),
    )

    # Execute action
    executed = execute_action(test_conn, action.action_id)
    assert executed.status == "SUCCEEDED"
    assert executed.executed_at is not None
    assert executed.result is not None
    assert executed.result["confirmed"] is True

    # Idempotent re-execution
    re_executed = execute_action(test_conn, action.action_id)
    assert re_executed.status == "SUCCEEDED"
    assert re_executed.executed_at == executed.executed_at

    # Check execution attempt history
    detail = get_action(test_conn, action.action_id)
    assert len(detail.execution_history) == 1
    assert detail.execution_history[0].status == "SUCCEEDED"


@pytest.mark.integration
def test_rejected_action_cannot_execute(test_conn, parent_scenario: str, action_test_tracker):
    """Rejected action cannot be executed."""
    req = ActionProposeRequest(
        scenario_id=parent_scenario,
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "estimated_cost": 55000000.0,
        },
    )
    action = propose_action(test_conn, req)
    action_test_tracker["action_ids"].append(action.action_id)

    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT approval_id FROM approval_requests WHERE action_id = %s;",
            (action.action_id,),
        )
        approval_id = cur.fetchone()[0]

    decide_approval_request(
        test_conn,
        str(approval_id),
        ApprovalDecisionRequest(status="REJECTED", decided_by="cfo", reason="Budget freeze"),
    )

    with pytest.raises(Exception) as exc:
        execute_action(test_conn, action.action_id)
    assert "rejected" in str(exc.value).lower()


@pytest.mark.integration
def test_action_api_endpoints(client: TestClient, parent_scenario: str, action_test_tracker):
    """API endpoints for action proposal, listing, detail, and execution."""
    headers = {"X-API-Key": "dev-operator-key"}
    prop_res = client.post(
        "/api/actions/propose",
        headers=headers,
        json={
            "scenario_id": parent_scenario,
            "action_type": "CREATE_PURCHASE_ORDER",
            "payload": {
                "supplier_id": "SUP-001",
                "item_id": "MAT-IRON",
                "estimated_cost": 10000.0,
            },
        },
    )
    assert prop_res.status_code == 201
    action_data = prop_res.json()
    action_id = action_data["action_id"]
    action_test_tracker["action_ids"].append(action_id)

    # List endpoint
    list_res = client.get(f"/api/actions/?scenario_id={parent_scenario}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Execute endpoint
    exec_res = client.post(f"/api/actions/{action_id}/execute", headers=headers)
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "SUCCEEDED"

    # Detail endpoint
    detail_res = client.get(f"/api/actions/{action_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["action"]["status"] == "SUCCEEDED"
    assert len(detail_res.json()["execution_history"]) >= 1
