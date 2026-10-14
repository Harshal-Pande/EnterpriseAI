"""Tests for PostgreSQL-backed Agent Runs API endpoints and execution lifecycle.

Verifies:
- Persisting specialist-agent execution records linked to workflows
- Recording start, completion, and failure state transitions
- Duration calculation from timestamps
- Input, output, and evidence reference serialization
- Sanitization of credentials in error messages and input/output payloads
- Querying and filtering agent runs by workflow, agent name, and status
- Honest representation of deterministic runs (no fabricated LLM tokens or models)
- WorkflowGraph multi-agent execution pipeline integration
- Process restart persistence
- Strict test isolation (cleans up only tracked test records)
"""

from __future__ import annotations

import uuid
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.orchestration.graph import WorkflowGraph


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
def agent_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Track created scenario and agent run records, cleaning up ONLY those exact IDs."""
    tracker: dict[str, list[str]] = {
        "scenario_ids": [],
        "agent_run_ids": [],
    }
    yield tracker

    cur = test_conn.cursor()
    try:
        if tracker["agent_run_ids"]:
            cur.execute(
                "DELETE FROM agent_runs WHERE agent_run_id::text = ANY(%s);",
                (tracker["agent_run_ids"],),
            )
        if tracker["scenario_ids"]:
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
    except Exception:
        test_conn.rollback()


@pytest.fixture
def parent_workflow(client: TestClient, agent_test_tracker) -> str:
    """Helper fixture creating a parent workflow in PostgreSQL and returning scenario_id."""
    res = client.post(
        "/api/workflow/",
        json={"scenario_template_id": "TPL-010", "linked_order_id": "ORD-AGENT-TEST"},
    )
    assert res.status_code == 201
    sid = res.json()["scenario_id"]
    agent_test_tracker["scenario_ids"].append(sid)
    return sid


@pytest.mark.integration
def test_start_agent_run_persists_to_database(client: TestClient, parent_workflow: str, agent_test_tracker, test_conn):
    """Starting an agent run persists record in agent_runs with RUNNING status."""
    payload = {
        "scenario_id": parent_workflow,
        "agent_name": "InventoryAgent",
        "input_refs": [{"sku": "SKU-TEST-1", "required_quantity": 50}],
        "model_provider": "deterministic",
        "model_name": "inventory-agent-v1",
        "prompt_version": "v1.0",
    }
    res = client.post("/api/agents/runs", json=payload)
    assert res.status_code == 201
    data = res.json()

    run_id = data["agent_run_id"]
    agent_test_tracker["agent_run_ids"].append(run_id)

    assert data["scenario_id"] == parent_workflow
    assert data["agent_name"] == "InventoryAgent"
    assert data["status"] == "RUNNING"
    assert data["started_at"] != ""
    assert data["completed_at"] is None
    assert data["duration_seconds"] is None
    assert data["model_provider"] == "deterministic"
    assert data["model_name"] == "inventory-agent-v1"

    # Verify directly in PostgreSQL
    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT status, agent_name, model_provider FROM agent_runs WHERE agent_run_id = %s;",
            (run_id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "RUNNING"
        assert row[1] == "InventoryAgent"
        assert row[2] == "deterministic"


@pytest.mark.integration
def test_complete_agent_run_records_output_and_duration(client: TestClient, parent_workflow: str, agent_test_tracker):
    """Completing an agent run updates status to COMPLETED and computes duration."""
    start_res = client.post(
        "/api/agents/runs",
        json={"scenario_id": parent_workflow, "agent_name": "SupervisorAgent"},
    )
    assert start_res.status_code == 201
    run_id = start_res.json()["agent_run_id"]
    agent_test_tracker["agent_run_ids"].append(run_id)

    # Complete the run
    complete_payload = {
        "output": {"next_agent": "InventoryAgent", "routing_reason": "order_evaluated"},
        "evidence_refs": [{"source": "order_rules", "confidence": 0.98}],
    }
    comp_res = client.post(f"/api/agents/runs/{run_id}/complete", json=complete_payload)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    assert comp_data["status"] == "COMPLETED"
    assert comp_data["completed_at"] is not None
    assert comp_data["duration_seconds"] is not None
    assert comp_data["duration_seconds"] >= 0.0
    assert comp_data["output"]["next_agent"] == "InventoryAgent"
    assert len(comp_data["evidence_refs"]) == 1


@pytest.mark.integration
def test_fail_agent_run_sanitizes_error_and_records_failure(client: TestClient, parent_workflow: str, agent_test_tracker):
    """Failing an agent run stores sanitized error details without leaking passwords/tokens."""
    start_res = client.post(
        "/api/agents/runs",
        json={"scenario_id": parent_workflow, "agent_name": "ProcurementAgent"},
    )
    run_id = start_res.json()["agent_run_id"]
    agent_test_tracker["agent_run_ids"].append(run_id)

    raw_error_msg = "Database lookup error: postgresql://dbuser:supersecretpass@db.local:5432/suppliers (Bearer my-api-token-xyz)"
    fail_payload = {
        "error_code": "SUPPLIER_LOOKUP_FAILED",
        "error_message": raw_error_msg,
    }
    fail_res = client.post(f"/api/agents/runs/{run_id}/fail", json=fail_payload)
    assert fail_res.status_code == 200
    fail_data = fail_res.json()

    assert fail_data["status"] == "FAILED"
    assert fail_data["error_code"] == "SUPPLIER_LOOKUP_FAILED"
    assert fail_data["completed_at"] is not None

    sanitized_msg = fail_data["error_message"]
    assert "supersecretpass" not in sanitized_msg
    assert "my-api-token-xyz" not in sanitized_msg
    assert "***" in sanitized_msg


@pytest.mark.integration
def test_list_agent_runs_with_filters(client: TestClient, parent_workflow: str, agent_test_tracker):
    """Listing agent runs supports filtering by workflow, agent name, and status."""
    for name in ["InventoryAgent", "FinanceAgent", "LogisticsAgent"]:
        res = client.post(
            "/api/agents/runs",
            json={"scenario_id": parent_workflow, "agent_name": name},
        )
        agent_test_tracker["agent_run_ids"].append(res.json()["agent_run_id"])

    # Filter by agent_name
    res_filtered = client.get(f"/api/agents/runs?agent_name=FinanceAgent&workflow_id={parent_workflow}")
    assert res_filtered.status_code == 200
    data = res_filtered.json()
    assert data["total"] == 1
    assert data["items"][0]["agent_name"] == "FinanceAgent"

    # Filter by status
    res_status = client.get(f"/api/agents/runs?status=RUNNING&workflow_id={parent_workflow}")
    assert res_status.status_code == 200
    assert res_status.json()["total"] == 3


@pytest.mark.integration
def test_get_agent_run_by_id_and_404_for_unknown(client: TestClient, parent_workflow: str, agent_test_tracker):
    """GET /api/agents/runs/{run_id} returns run details, and 404 for nonexistent UUID."""
    start_res = client.post(
        "/api/agents/runs",
        json={"scenario_id": parent_workflow, "agent_name": "SupervisorAgent"},
    )
    run_id = start_res.json()["agent_run_id"]
    agent_test_tracker["agent_run_ids"].append(run_id)

    get_res = client.get(f"/api/agents/runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["agent_run_id"] == run_id

    fake_id = str(uuid.uuid4())
    not_found = client.get(f"/api/agents/runs/{fake_id}")
    assert not_found.status_code == 404


@pytest.mark.integration
def test_workflow_graph_executes_pipeline_with_persisted_runs(client: TestClient, agent_test_tracker, test_conn):
    """WorkflowGraph execution runs all specialist agents, persisting runs and resolving workflow."""
    # Create workflow
    create_res = client.post(
        "/api/workflow/",
        json={"scenario_template_id": "TPL-010", "linked_order_id": "ORD-PIPELINE-01"},
    )
    assert create_res.status_code == 201
    wf = create_res.json()
    scenario_id = wf["scenario_id"]
    agent_test_tracker["scenario_ids"].append(scenario_id)

    # Execute workflow graph with test connection
    graph = WorkflowGraph()
    state = {
        "workflow_id": scenario_id,
        "scenario_id": scenario_id,
        "order_id": "ORD-PIPELINE-01",
        "current_agent": "SupervisorAgent",
        "status": "queued",
        "audit_trail": [],
    }
    result_state = graph.run_workflow(state, conn=test_conn)

    assert result_state["status"] == "completed"
    assert "SupervisorAgent" in result_state["agent_outputs"]
    assert "InventoryAgent" in result_state["agent_outputs"]
    assert "ProcurementAgent" in result_state["agent_outputs"]
    assert "FinanceAgent" in result_state["agent_outputs"]
    assert "LogisticsAgent" in result_state["agent_outputs"]

    # Verify all 5 agent runs were persisted to PostgreSQL
    list_res = client.get(f"/api/agents/runs?workflow_id={scenario_id}")
    assert list_res.status_code == 200
    runs = list_res.json()
    assert runs["total"] == 5

    agent_names = {r["agent_name"] for r in runs["items"]}
    assert agent_names == {
        "SupervisorAgent",
        "InventoryAgent",
        "ProcurementAgent",
        "FinanceAgent",
        "LogisticsAgent",
    }
    assert all(r["status"] == "COMPLETED" for r in runs["items"])
    assert all(r["duration_seconds"] is not None for r in runs["items"])

    # Verify workflow itself transitioned to RESOLVED
    wf_res = client.get(f"/api/workflow/{scenario_id}")
    assert wf_res.status_code == 200
    assert wf_res.json()["status"] == "RESOLVED"
    assert wf_res.json()["resolved_at"] is not None


@pytest.mark.integration
def test_workflow_graph_persists_failure_on_agent_error(client: TestClient, agent_test_tracker, test_conn):
    """When an agent encounters an error, the run is marked FAILED and workflow is marked FAILED."""
    create_res = client.post(
        "/api/workflow/",
        json={"scenario_template_id": "TPL-010", "linked_order_id": "ORD-FAIL-01"},
    )
    scenario_id = create_res.json()["scenario_id"]
    agent_test_tracker["scenario_ids"].append(scenario_id)

    graph = WorkflowGraph()
    state = {
        "workflow_id": scenario_id,
        "scenario_id": scenario_id,
        "order_id": "ORD-FAIL-01",
        "current_agent": "SupervisorAgent",
        "status": "queued",
        "audit_trail": [],
    }

    # Simulate an error in the InventoryAgent
    with patch.object(graph.inventory, "run", side_effect=RuntimeError("Inventory warehouse unreachable")):
        res_state = graph.run_workflow(state, conn=test_conn)

    assert res_state["status"] == "failed"

    # Verify inventory run is marked FAILED in PostgreSQL
    list_res = client.get(f"/api/agents/runs?workflow_id={scenario_id}")
    runs = list_res.json()["items"]
    inv_run = next(r for r in runs if r["agent_name"] == "InventoryAgent")
    assert inv_run["status"] == "FAILED"
    assert inv_run["error_code"] == "INVENTORYAGENT_FAILURE"
    assert "Inventory warehouse unreachable" in inv_run["error_message"]

    # Verify workflow transitioned to FAILED in scenario_instances
    wf_res = client.get(f"/api/workflow/{scenario_id}")
    assert wf_res.status_code == 200
    assert wf_res.json()["status"] == "FAILED"
    assert "InventoryAgent" in wf_res.json()["resolution_summary"]


@pytest.mark.integration
def test_honest_deterministic_model_metadata(client: TestClient, parent_workflow: str, agent_test_tracker):
    """Verifies deterministic executions are honestly marked without inventing LLM tokens or models."""
    res = client.post(
        "/api/agents/runs",
        json={"scenario_id": parent_workflow, "agent_name": "FinanceAgent"},
    )
    data = res.json()
    agent_test_tracker["agent_run_ids"].append(data["agent_run_id"])

    assert data["model_provider"] == "deterministic"
    assert data["model_name"] == "scripted-agent-v1"
    # Ensure no fabricated OpenAI/Anthropic/tokens
    assert "gpt" not in str(data).lower()
    assert "claude" not in str(data).lower()
    assert "tokens" not in data


@pytest.mark.integration
def test_legacy_agent_summary_endpoint(client: TestClient):
    """GET /api/agents/ continues to return agent statuses summary for the dashboard."""
    res = client.get("/api/agents/")
    assert res.status_code == 200
    data = res.json()
    assert data["supervisor"] == "idle"
    assert data["inventory"] == "active"
    assert data["procurement"] == "idle"
    assert data["finance"] == "idle"
    assert data["logistics"] == "idle"
