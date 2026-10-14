"""Tests for PostgreSQL-backed Workflow API endpoints and state transitions.

Verifies:
- Creating workflow instances and persisting to scenario_instances
- Retrieving workflow by ID and listing with filtering and pagination
- Valid and invalid state transitions with validation rules
- Audit trail logging in event_log for all transitions
- Sanitization of error messages and failure summaries
- Idempotency preservation
- Process restart persistence
- Strict test isolation (cleans up only tracked test records)
"""

from __future__ import annotations

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def client(test_database_url, monkeypatch) -> TestClient:
    """TestClient configured with TEST_DATABASE_URL."""
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    init_db_pool(database_url=test_database_url)
    with TestClient(app) as test_client:
        yield test_client
    close_db_pool()


@pytest.fixture
def workflow_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Track created workflow, agent run, and audit records, cleaning up ONLY those exact IDs."""
    tracker: dict[str, list[str]] = {
        "scenario_ids": [],
        "agent_run_ids": [],
        "event_ids": [],
    }
    yield tracker

    cur = test_conn.cursor()
    try:
        if tracker["agent_run_ids"]:
            cur.execute(
                "DELETE FROM agent_findings WHERE agent_run_id::text = ANY(%s);",
                (tracker["agent_run_ids"],),
            )
            cur.execute(
                "DELETE FROM agent_runs WHERE agent_run_id::text = ANY(%s);",
                (tracker["agent_run_ids"],),
            )
        if tracker["scenario_ids"]:
            cur.execute(
                "DELETE FROM policy_evaluations WHERE decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id::text = ANY(%s));",
                (tracker["scenario_ids"],),
            )
            cur.execute(
                "DELETE FROM decisions WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
            # Also clean up any agent_runs and findings linked to these scenarios
            cur.execute(
                "DELETE FROM agent_findings WHERE scenario_id::text = ANY(%s) OR agent_run_id IN (SELECT agent_run_id FROM agent_runs WHERE scenario_id::text = ANY(%s));",
                (tracker["scenario_ids"], tracker["scenario_ids"]),
            )
            cur.execute(
                "DELETE FROM agent_runs WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
            # Clean up event_log entries for these scenarios
            cur.execute(
                "DELETE FROM event_log WHERE scenario_id::text = ANY(%s) OR entity_id::text = ANY(%s);",
                (tracker["scenario_ids"], tracker["scenario_ids"]),
            )
            cur.execute(
                "DELETE FROM scenario_instances WHERE scenario_id::text = ANY(%s);",
                (tracker["scenario_ids"],),
            )
        if tracker["event_ids"]:
            cur.execute(
                "DELETE FROM event_log WHERE event_id::text = ANY(%s);",
                (tracker["event_ids"],),
            )
        test_conn.commit()
    except Exception as exc:
        test_conn.rollback()
        raise exc


@pytest.mark.integration
def test_create_workflow_persists_to_database(client: TestClient, workflow_test_tracker, test_conn):
    """Creating a workflow persists it in scenario_instances and logs to event_log."""
    payload = {
        "scenario_template_id": "TPL-010",
        "linked_order_id": "ORD-TEST-001",
        "severity": "LOW",
        "input_overlay": {"priority": "standard", "note": "Integration test run"},
        "idempotency_key": f"IDEMP-{uuid.uuid4()}",
    }
    res = client.post("/api/workflow/", json=payload)
    assert res.status_code == 201
    data = res.json()

    scenario_id = data["scenario_id"]
    workflow_test_tracker["scenario_ids"].append(scenario_id)

    assert data["workflow_id"] == scenario_id
    assert data["status"] == "QUEUED"
    assert data["linked_order_id"] == "ORD-TEST-001"
    assert data["scenario_template_id"] == "TPL-010"
    assert data["severity"] == "LOW"
    assert data["idempotency_key"] == payload["idempotency_key"]

    # Verify directly in PostgreSQL
    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT status, linked_order_id, severity FROM scenario_instances WHERE scenario_id = %s;",
            (scenario_id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "QUEUED"
        assert row[1] == "ORD-TEST-001"
        assert row[2] == "LOW"

        # Verify audit log entry in event_log
        cur.execute(
            "SELECT event_type, entity_id, status FROM event_log WHERE scenario_id = %s;",
            (scenario_id,),
        )
        audit_row = cur.fetchone()
        assert audit_row is not None
        assert audit_row[0] == "WORKFLOW_CREATED"
        assert audit_row[1] == scenario_id
        assert audit_row[2] == "QUEUED"


@pytest.mark.integration
def test_workflow_idempotency_prevents_duplicate_creation(client: TestClient, workflow_test_tracker):
    """Submitting the same idempotency_key returns existing workflow without duplicates."""
    idemp_key = f"IDEMP-DUP-{uuid.uuid4()}"
    payload = {
        "scenario_template_id": "TPL-010",
        "linked_order_id": "ORD-TEST-DUP",
        "idempotency_key": idemp_key,
    }

    res1 = client.post("/api/workflow/", json=payload)
    assert res1.status_code == 201
    wf1 = res1.json()
    workflow_test_tracker["scenario_ids"].append(wf1["scenario_id"])

    res2 = client.post("/api/workflow/", json=payload)
    assert res2.status_code == 201
    wf2 = res2.json()

    # Must return exact same workflow instance ID
    assert wf1["scenario_id"] == wf2["scenario_id"]
    assert wf1["idempotency_key"] == wf2["idempotency_key"]


@pytest.mark.integration
def test_get_workflow_by_id(client: TestClient, workflow_test_tracker):
    """Retrieving a persisted workflow by UUID returns full details."""
    payload = {
        "scenario_template_id": "TPL-001",
        "linked_order_id": "ORD-TEST-FETCH",
        "severity": "HIGH",
    }
    create_res = client.post("/api/workflow/", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    wf_id = created["scenario_id"]
    workflow_test_tracker["scenario_ids"].append(wf_id)

    get_res = client.get(f"/api/workflow/{wf_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()

    assert fetched["scenario_id"] == wf_id
    assert fetched["scenario_template_id"] == "TPL-001"
    assert fetched["severity"] == "HIGH"
    assert fetched["status"] == "QUEUED"


@pytest.mark.integration
def test_get_workflow_nonexistent_returns_404(client: TestClient):
    """Retrieving a nonexistent UUID returns 404 Not Found."""
    fake_uuid = str(uuid.uuid4())
    res = client.get(f"/api/workflow/{fake_uuid}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.integration
def test_list_workflows_with_filters_and_pagination(client: TestClient, workflow_test_tracker):
    """Listing workflows supports status filter, order_id filter, and deterministic pagination."""
    created_ids = []
    for i in range(3):
        payload = {
            "scenario_template_id": "TPL-010",
            "linked_order_id": f"ORD-FILTER-{i}",
            "severity": "LOW",
        }
        res = client.post("/api/workflow/", json=payload)
        assert res.status_code == 201
        sid = res.json()["scenario_id"]
        created_ids.append(sid)
        workflow_test_tracker["scenario_ids"].append(sid)

    # Filter by linked_order_id
    res_filtered = client.get("/api/workflow/?order_id=ORD-FILTER-1")
    assert res_filtered.status_code == 200
    data = res_filtered.json()
    assert data["total"] >= 1
    assert any(item["linked_order_id"] == "ORD-FILTER-1" for item in data["items"])

    # Pagination test
    res_page = client.get("/api/workflow/?limit=2&offset=0")
    assert res_page.status_code == 200
    pdata = res_page.json()
    assert len(pdata["items"]) <= 2
    assert pdata["limit"] == 2
    assert pdata["offset"] == 0


@pytest.mark.integration
def test_valid_workflow_state_transitions(client: TestClient, workflow_test_tracker, test_conn):
    """Workflow transitions from QUEUED -> RUNNING -> RESOLVED succeed and log to event_log."""
    res_create = client.post(
        "/api/workflow/",
        json={"scenario_template_id": "TPL-010", "linked_order_id": "ORD-TRANS-01"},
    )
    assert res_create.status_code == 201
    wf_id = res_create.json()["scenario_id"]
    workflow_test_tracker["scenario_ids"].append(wf_id)

    # Transition 1: QUEUED -> RUNNING
    trans1 = client.post(
        f"/api/workflow/{wf_id}/transition",
        json={"new_status": "RUNNING", "reason_code": "DISPATCHED", "actor_id": "SupervisorAgent"},
    )
    assert trans1.status_code == 200
    assert trans1.json()["status"] == "RUNNING"

    # Transition 2: RUNNING -> RESOLVED
    trans2 = client.post(
        f"/api/workflow/{wf_id}/transition",
        json={
            "new_status": "RESOLVED",
            "reason_code": "ALL_STEPS_COMPLETED",
            "resolution_summary": "Order successfully fulfilled and dispatched.",
        },
    )
    assert trans2.status_code == 200
    assert trans2.json()["status"] == "RESOLVED"
    assert trans2.json()["resolved_at"] is not None

    # Check event_log contains both transition records
    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT event_type, status, reason_code FROM event_log WHERE scenario_id = %s ORDER BY event_timestamp ASC;",
            (wf_id,),
        )
        rows = cur.fetchall()
        # Expect WORKFLOW_CREATED, WORKFLOW_TRANSITION (RUNNING), WORKFLOW_TRANSITION (RESOLVED)
        assert len(rows) >= 3
        statuses = [r[1] for r in rows]
        assert "QUEUED" in statuses
        assert "RUNNING" in statuses
        assert "RESOLVED" in statuses


@pytest.mark.integration
def test_invalid_state_transition_is_rejected(client: TestClient, workflow_test_tracker):
    """Invalid transitions (e.g. directly QUEUED -> RESOLVED or transition from terminal state) are rejected with 400."""
    res_create = client.post(
        "/api/workflow/",
        json={"scenario_template_id": "TPL-010", "linked_order_id": "ORD-INVALID-TRANS"},
    )
    wf_id = res_create.json()["scenario_id"]
    workflow_test_tracker["scenario_ids"].append(wf_id)

    # Invalid: QUEUED cannot jump directly to RESOLVED
    invalid_res = client.post(
        f"/api/workflow/{wf_id}/transition",
        json={"new_status": "RESOLVED"},
    )
    assert invalid_res.status_code == 400
    assert "Invalid state transition" in invalid_res.json()["detail"]

    # Transition to CANCELLED (terminal state)
    cancel_res = client.post(
        f"/api/workflow/{wf_id}/transition",
        json={"new_status": "CANCELLED", "reason_code": "USER_ABORT"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Any transition from CANCELLED must be rejected
    from_terminal = client.post(
        f"/api/workflow/{wf_id}/transition",
        json={"new_status": "RUNNING"},
    )
    assert from_terminal.status_code == 400
    assert "terminal state" in from_terminal.json()["detail"].lower()


@pytest.mark.integration
def test_error_and_secret_sanitization(client: TestClient, workflow_test_tracker):
    """Sanitizes connection strings, passwords, and sensitive keys in failures and inputs."""
    sensitive_overlay = {
        "database_url": "postgresql://admin:supersecretpassword@db.internal:5432/proddb",
        "api_key": "secret-token-xyz-12345",
        "customer_note": "Confidential order",
    }
    create_res = client.post(
        "/api/workflow/",
        json={
            "scenario_template_id": "TPL-010",
            "linked_order_id": "ORD-SANITIZE-01",
            "input_overlay": sensitive_overlay,
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    wf_id = created["scenario_id"]
    workflow_test_tracker["scenario_ids"].append(wf_id)

    # Sensitive overlay keys must be masked
    assert created["input_overlay"]["database_url"] == "***"
    assert created["input_overlay"]["api_key"] == "***"
    assert "supersecretpassword" not in str(created)

    # Transition to RUNNING
    client.post(f"/api/workflow/{wf_id}/transition", json={"new_status": "RUNNING"})

    # Fail with error containing credentials
    raw_error = "Connection failed: postgresql://dbuser:mypassword123@prod-cluster:5432/orders (Bearer mysecrettoken)"
    fail_res = client.post(
        f"/api/workflow/{wf_id}/transition",
        json={
            "new_status": "FAILED",
            "reason_code": "SYSTEM_ERROR",
            "resolution_summary": raw_error,
        },
    )
    assert fail_res.status_code == 200
    summary = fail_res.json()["resolution_summary"]
    assert "mypassword123" not in summary
    assert "mysecrettoken" not in summary
    assert "***" in summary


@pytest.mark.integration
def test_process_restart_preserves_workflow_state(client: TestClient, workflow_test_tracker, test_database_url, monkeypatch):
    """Workflow instance and status persist across connection pool teardown and restart."""
    res_create = client.post(
        "/api/workflow/",
        json={"scenario_template_id": "TPL-010", "linked_order_id": "ORD-RESTART-01"},
    )
    assert res_create.status_code == 201
    wf_id = res_create.json()["scenario_id"]
    workflow_test_tracker["scenario_ids"].append(wf_id)

    # Advance to RUNNING
    client.post(f"/api/workflow/{wf_id}/transition", json={"new_status": "RUNNING"})

    # Simulate application restart: tear down pool completely
    close_db_pool()
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    init_db_pool(database_url=test_database_url)

    # Query with newly initialized pool
    with TestClient(app) as new_client:
        get_res = new_client.get(f"/api/workflow/{wf_id}")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["scenario_id"] == wf_id
        assert data["status"] == "RUNNING"
        assert data["linked_order_id"] == "ORD-RESTART-01"


@pytest.mark.integration
def test_legacy_endpoint_compatibility(client: TestClient):
    """Legacy routes GET /api/workflow/status and GET /api/workflow/wf-101 remain fully functional."""
    res1 = client.get("/api/workflow/status")
    assert res1.status_code == 200
    assert res1.json()["current_agent"] == "InventoryAgent"

    res2 = client.get("/api/workflow/wf-101")
    assert res2.status_code == 200
    assert res2.json()["status"] == "active"
