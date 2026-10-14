"""End-to-End Integration Lifecycle Tests (Task 14).

Verifies the complete supply chain control room lifecycle:
1. Scenario workflow initiation and persistence
2. Specialist-agent pipeline execution and database-grounded reasoning
3. Deterministic policy gating and approval requirement detection
4. Blocked execution while unapproved
5. Authorized human approval decision with audit trail
6. Action execution through SafeSimulationAdapter and result persistence
7. Audit event logging and canonical hashing
8. Blockchain anchor verification (MATCHED vs tampered MISMATCH)
9. Strict test isolation and clean teardown
"""

from __future__ import annotations

import json
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.models.action import ActionProposeRequest
from app.models.blockchain import AnchorEventRequest
from app.models.policy import ApprovalDecisionRequest, PolicyEvaluationRequest
from app.models.workflow import WorkflowCreateRequest
from app.orchestration.graph import WorkflowGraph
from app.services.action_service import execute_action, get_action, propose_action
from app.services.approval_service import decide_approval_request
from app.services.blockchain_service import (
    CanonicalHasher,
    anchor_audit_event,
    verify_anchor_integrity,
)
from app.services.policy_service import evaluate_policy
from app.services.workflow_service import create_workflow, get_workflow


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def client(test_database_url, monkeypatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    init_db_pool(database_url=test_database_url)
    with TestClient(app) as test_client:
        yield test_client
    close_db_pool()


@pytest.fixture
def e2e_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Track all created test records and clean up in exact foreign-key dependency order."""
    tracker: dict[str, list[str]] = {
        "scenario_ids": [],
        "action_ids": [],
        "event_ids": [],
        "anchor_ids": [],
        "eval_ids": [],
    }
    yield tracker

    cur = test_conn.cursor()
    try:
        if tracker["anchor_ids"]:
            cur.execute(
                "DELETE FROM blockchain_anchors WHERE anchor_id::text = ANY(%s);",
                (tracker["anchor_ids"],),
            )
        if tracker["event_ids"]:
            cur.execute(
                "DELETE FROM blockchain_anchors WHERE event_id_or_batch_id = ANY(%s);",
                (tracker["event_ids"],),
            )
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


@pytest.mark.integration
def test_e2e_full_governed_lifecycle(test_conn, e2e_test_tracker):
    """Full end-to-end lifecycle from workflow to specialist agents, policy, approval, action, and audit anchor."""
    # 1. Create and persist scenario workflow
    wf_req = WorkflowCreateRequest(
        scenario_template_id="TPL-010",
        linked_order_id=f"E2E-ORD-{uuid.uuid4().hex[:6].upper()}",
        severity="HIGH",
        input_overlay={"e2e_test": True},
        execute_immediately=True,
    )
    workflow = create_workflow(test_conn, wf_req)
    scenario_id = workflow.scenario_id
    e2e_test_tracker["scenario_ids"].append(scenario_id)

    assert workflow.status in {"QUEUED", "RUNNING"}

    # 2. Execute specialist-agent pipeline
    graph = WorkflowGraph()
    initial_state = {
        "workflow_id": workflow.workflow_id,
        "scenario_id": scenario_id,
        "order_id": workflow.linked_order_id,
        "current_agent": "SupervisorAgent",
        "status": "queued",
        "audit_trail": [],
    }
    graph_res = graph.run_workflow(initial_state, conn=test_conn)
    assert graph_res.get("status") in {"completed", "waiting_approval"}

    # 3. Propose consequential procurement action exceeding INR 50M threshold
    action_req = ActionProposeRequest(
        scenario_id=scenario_id,
        action_type="CREATE_PURCHASE_ORDER",
        target_entity_id="SUP-001",
        payload={
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "quantity": 200.0,
            "estimated_cost": 55000000.0,  # 55M > 50M threshold
        },
    )
    action = propose_action(test_conn, action_req)
    action_id = action.action_id
    e2e_test_tracker["action_ids"].append(action_id)

    # 4. Verify policy gate blocks unapproved action
    assert action.status == "PROPOSED"
    assert action.requires_approval is True

    with pytest.raises(Exception) as exc_info:
        execute_action(test_conn, action_id)
    assert "requires human approval" in str(exc_info.value).lower()

    # 5. Locate approval request and authorize decision
    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT approval_id FROM approval_requests WHERE action_id = %s;",
            (action_id,),
        )
        appr_row = cur.fetchone()
        assert appr_row is not None
        approval_id = str(appr_row[0])

    decision_req = ApprovalDecisionRequest(
        status="APPROVED",
        decided_by="chief_procurement_officer",
        reason="Approved under critical operational maintenance contingency.",
    )
    approved_rec = decide_approval_request(test_conn, approval_id, decision_req)
    assert approved_rec.status == "APPROVED"
    assert approved_rec.decided_by == "chief_procurement_officer"

    # 6. Execute action through safe simulation adapter
    executed_action = execute_action(test_conn, action_id)
    assert executed_action.status == "SUCCEEDED"
    assert executed_action.result is not None
    assert executed_action.result["execution_mode"] == "SIMULATION"
    assert executed_action.result["confirmed"] is True
    assert "SIM-" in executed_action.result["reference_number"]

    # 7. Record and anchor audit event
    event_id = f"EVT-E2E-{uuid.uuid4().hex[:8]}"
    e2e_test_tracker["event_ids"].append(event_id)
    event_payload = {
        "event_id": event_id,
        "scenario_id": scenario_id,
        "action_id": action_id,
        "action_type": "CREATE_PURCHASE_ORDER",
        "approved_by": "chief_procurement_officer",
        "result_reference": executed_action.result["reference_number"],
    }
    anchor_req = AnchorEventRequest(
        event_id=event_id,
        payload=event_payload,
        force_simulation=True,
    )
    anchor_rec = anchor_audit_event(test_conn, anchor_req)
    e2e_test_tracker["anchor_ids"].append(anchor_rec.anchor_id)

    assert anchor_rec.confirmation_status in {"CONFIRMED", "NOT_SUBMITTED"}
    assert anchor_rec.payload_hash.startswith("0x")

    # 8. Cryptographic integrity verification
    verif_match = verify_anchor_integrity(test_conn, event_id, event_payload)
    assert verif_match.matched is True
    assert verif_match.verification_status == "MATCHED"

    # 9. Tampered payload detection
    tampered_payload = {**event_payload, "approved_by": "unauthorized_forged_actor"}
    verif_tampered = verify_anchor_integrity(test_conn, event_id, tampered_payload)
    assert verif_tampered.matched is False
    assert verif_tampered.verification_status == "MISMATCH"


@pytest.mark.integration
def test_e2e_rejected_action_path(test_conn, e2e_test_tracker):
    """Rejected approval request strictly blocks execution."""
    wf_req = WorkflowCreateRequest(
        scenario_template_id="TPL-010",
        linked_order_id=f"REJ-ORD-{uuid.uuid4().hex[:6].upper()}",
        severity="MEDIUM",
    )
    wf = create_workflow(test_conn, wf_req)
    e2e_test_tracker["scenario_ids"].append(wf.scenario_id)

    action_req = ActionProposeRequest(
        scenario_id=wf.scenario_id,
        action_type="CREATE_PURCHASE_ORDER",
        payload={
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "quantity": 100.0,
            "estimated_cost": 55000000.0,
        },
    )
    action = propose_action(test_conn, action_req)
    e2e_test_tracker["action_ids"].append(action.action_id)

    with test_conn.cursor() as cur:
        cur.execute("SELECT approval_id FROM approval_requests WHERE action_id = %s;", (action.action_id,))
        appr_id = str(cur.fetchone()[0])

    # Reject
    decide_approval_request(
        test_conn,
        appr_id,
        ApprovalDecisionRequest(status="REJECTED", decided_by="cfo", reason="Quarterly budget freeze."),
    )

    # Attempt execution must be rejected
    with pytest.raises(Exception) as exc:
        execute_action(test_conn, action.action_id)
    assert "rejected" in str(exc.value).lower()
