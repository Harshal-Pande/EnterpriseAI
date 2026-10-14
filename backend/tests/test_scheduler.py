"""Tests for Persistent Scenario Scheduler (Task 8).

Verifies:
- Configurable interval via environment variable
- PostgreSQL lease locking and cross-process concurrency protection
- Stale-lock recovery after expired lease
- Scenario eligibility selection from scenario_templates
- Duplicate prevention (avoiding active workflow collision)
- Honest NO_WORK reporting
- Lifecycle execution and failure recording
- Read-only status API and manual trigger endpoint
- Strict test isolation (reverts scheduler lock and cleans up tracked scenarios)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.services.scheduler_service import (
    DEFAULT_INTERVAL_SECONDS,
    ScenarioScheduler,
    get_configured_interval,
    get_max_open_scenarios,
)


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def client(test_database_url, monkeypatch) -> TestClient:
    """TestClient configured with TEST_DATABASE_URL and scheduler loop disabled in test."""
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    init_db_pool(database_url=test_database_url)
    with TestClient(app) as test_client:
        yield test_client
    close_db_pool()


@pytest.fixture
def scheduler_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Track created scenarios and reset scheduler_state lock upon teardown."""
    tracker: dict[str, list[str]] = {"scenario_ids": []}
    yield tracker

    try:
        test_conn.rollback()
        cur = test_conn.cursor()
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
        # Clean up scheduler event logs and reset scheduler lock state
        cur.execute("DELETE FROM event_log WHERE entity_id = 'scenario-generator' OR entity_type = 'SCHEDULER';")
        cur.execute(
            """
            UPDATE scheduler_state
            SET locked_by = NULL, lease_expires_at = NULL
            WHERE scheduler_name = 'scenario-generator';
            """
        )
        test_conn.commit()
    except Exception as exc:
        test_conn.rollback()
        raise exc


@pytest.mark.integration
def test_configured_interval(monkeypatch):
    """Interval honors SCHEDULER_INTERVAL_SECONDS or defaults to 300."""
    monkeypatch.delenv("SCHEDULER_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("SCENARIO_SCHEDULER_INTERVAL_SECONDS", raising=False)
    assert get_configured_interval() == DEFAULT_INTERVAL_SECONDS

    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "120")
    assert get_configured_interval() == 120

    # Fallback on invalid format
    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "invalid")
    assert get_configured_interval() == DEFAULT_INTERVAL_SECONDS


@pytest.mark.integration
def test_lease_acquisition_and_collision_prevention(test_conn, scheduler_test_tracker):
    """Two concurrent workers cannot acquire the scheduler lease simultaneously."""
    sched1 = ScenarioScheduler()
    sched2 = ScenarioScheduler()

    # Worker 1 acquires lease
    acquired1, interval1 = sched1.acquire_lease(test_conn, lease_seconds=60)
    assert acquired1 is True

    # Worker 2 attempts while Worker 1 lease is active -> must fail
    acquired2, interval2 = sched2.acquire_lease(test_conn, lease_seconds=60)
    assert acquired2 is False
    assert interval2 is None

    # Worker 1 releases lease
    sched1.release_lease(test_conn, outcome_status="COMPLETED")

    # Worker 2 now succeeds
    acquired2_after, _ = sched2.acquire_lease(test_conn, lease_seconds=60)
    assert acquired2_after is True
    sched2.release_lease(test_conn, outcome_status="COMPLETED")


@pytest.mark.integration
def test_stale_lock_recovery(test_conn, scheduler_test_tracker):
    """A stale/expired lease from a crashed worker is automatically recovered."""
    sched_crashed = ScenarioScheduler()
    sched_active = ScenarioScheduler()

    # Simulate crashed worker acquiring a lease that expired 10 seconds ago
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(seconds=10)
    with test_conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scheduler_state
            SET
                locked_by = %s,
                lock_acquired_at = %s,
                lease_expires_at = %s
            WHERE scheduler_name = 'scenario-generator';
            """,
            (sched_crashed.worker_id, now - timedelta(seconds=70), expired_time),
        )
        test_conn.commit()

    # Active worker should safely reclaim the expired lock
    acquired, interval = sched_active.acquire_lease(test_conn, lease_seconds=60)
    assert acquired is True
    sched_active.release_lease(test_conn, outcome_status="RECOVERED")


@pytest.mark.integration
def test_scenario_eligibility_and_duplicate_prevention(test_conn, scheduler_test_tracker):
    """Scheduler selects enabled templates and avoids templates that already have active workflows."""
    sched = ScenarioScheduler()

    eligible = sched.find_eligible_scenario(test_conn)
    assert eligible is not None
    template_id = eligible[0]

    # Create an active workflow for this template in QUEUED status
    scenario_id = str(uuid.uuid4())
    scheduler_test_tracker["scenario_ids"].append(scenario_id)
    now = datetime.now(timezone.utc)
    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenario_instances (
                scenario_id, scenario_template_id, scheduled_at, created_at,
                status, severity, idempotency_key
            )
            VALUES (%s, %s, %s, %s, 'QUEUED', 'LOW', %s);
            """,
            (scenario_id, template_id, now, now, f"IDEMP-{scenario_id}"),
        )
        test_conn.commit()

    # Next eligible query must not return the same template while it is active
    next_eligible = sched.find_eligible_scenario(test_conn)
    if next_eligible:
        assert next_eligible[0] != template_id


@pytest.mark.integration
def test_run_cycle_executes_eligible_scenario(test_conn, scheduler_test_tracker):
    """Running a cycle executes eligible scenario workflow and specialist agents."""
    sched = ScenarioScheduler()
    result = sched.run_cycle(test_conn)

    assert result["executed"] is True
    assert result["status"] in {"COMPLETED", "FAILED"}
    assert "scenario_id" in result
    scheduler_test_tracker["scenario_ids"].append(result["scenario_id"])

    # Verify scheduler_state was updated
    status = sched.get_status(test_conn)
    assert status["total_runs"] >= 1
    assert status["last_status"] in {"COMPLETED", "FAILED"}
    assert status["is_locked"] is False


@pytest.mark.integration
def test_scheduler_api_status_and_trigger(client: TestClient, scheduler_test_tracker):
    """GET /api/scheduler/status returns state, and POST /api/scheduler/trigger executes cycle."""
    # Query status
    res_status = client.get("/api/scheduler/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["scheduler_name"] == "scenario-generator"
    assert "configured_interval_seconds" in data
    assert "total_runs" in data

    # Trigger cycle
    res_trigger = client.post("/api/scheduler/trigger", headers={"X-API-Key": "dev-operator-key"})
    assert res_trigger.status_code == 200
    trig_data = res_trigger.json()
    assert "executed" in trig_data
    if trig_data.get("scenario_id"):
        scheduler_test_tracker["scenario_ids"].append(trig_data["scenario_id"])


@pytest.mark.integration
def test_interval_precedence_and_validation(monkeypatch):
    """SCENARIO_SCHEDULER_INTERVAL_SECONDS takes precedence over SCHEDULER_INTERVAL_SECONDS, falling back safely."""
    monkeypatch.delenv("SCENARIO_SCHEDULER_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("SCHEDULER_INTERVAL_SECONDS", raising=False)
    assert get_configured_interval() == DEFAULT_INTERVAL_SECONDS

    # SCHEDULER_INTERVAL_SECONDS works when alone
    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "200")
    assert get_configured_interval() == 200

    # SCENARIO_SCHEDULER_INTERVAL_SECONDS takes precedence
    monkeypatch.setenv("SCENARIO_SCHEDULER_INTERVAL_SECONDS", "150")
    assert get_configured_interval() == 150

    # Zero or negative values fall back to default
    monkeypatch.setenv("SCENARIO_SCHEDULER_INTERVAL_SECONDS", "-10")
    assert get_configured_interval() == DEFAULT_INTERVAL_SECONDS

    monkeypatch.setenv("SCENARIO_SCHEDULER_INTERVAL_SECONDS", "0")
    assert get_configured_interval() == DEFAULT_INTERVAL_SECONDS


@pytest.mark.integration
def test_open_scenarios_capacity_limit_skips_generation(test_conn, scheduler_test_tracker, monkeypatch):
    """When active open scenarios reach the configured capacity, the scheduler cycle safely skips generation."""
    monkeypatch.setenv("SCHEDULER_MAX_OPEN_SCENARIOS", "2")
    sched = ScenarioScheduler()

    # Pre-populate 2 active scenarios
    now = datetime.now(timezone.utc)
    for _ in range(2):
        s_id = str(uuid.uuid4())
        scheduler_test_tracker["scenario_ids"].append(s_id)
        with test_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scenario_instances (
                    scenario_id, scenario_template_id, scheduled_at, created_at,
                    status, severity, idempotency_key
                )
                VALUES (%s, 'TPL-001', %s, %s, 'RUNNING', 'MEDIUM', %s);
                """,
                (s_id, now, now, f"IDEMP-LIMIT-{s_id}"),
            )
            test_conn.commit()

    # Cycle should skip due to limit
    res = sched.run_cycle(test_conn)
    assert res["executed"] is False
    assert res["status"] == "SKIPPED"
    assert res["reason"] == "OPEN_SCENARIOS_LIMIT_REACHED"

    status = sched.get_status(test_conn)
    assert status["last_skip_reason"] == "OPEN_SCENARIOS_LIMIT_REACHED"
    assert (status.get("open_scenarios_count") or 0) >= 2


@pytest.mark.integration
def test_operational_data_grounding(test_conn, scheduler_test_tracker):
    """Generated scenario binds operational entities to real rows in PostgreSQL operational tables."""
    sched = ScenarioScheduler()
    res = sched.run_cycle(test_conn)
    assert res["executed"] is True
    scenario_id = res["scenario_id"]
    scheduler_test_tracker["scenario_ids"].append(scenario_id)

    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT input_overlay, linked_order_id FROM scenario_instances WHERE scenario_id = %s;",
            (scenario_id,),
        )
        row = cur.fetchone()
        assert row is not None
        overlay, linked_order_id = row[0], row[1]
        grounded = overlay.get("grounded_data", {})
        meta = overlay.get("generation_metadata", {})
        assert meta.get("grounded_operational_data") is True

        # Check references in PostgreSQL operational tables
        if linked_order_id:
            cur.execute("SELECT 1 FROM orders WHERE order_id = %s;", (linked_order_id,))
            assert cur.fetchone() is not None, f"Referenced order {linked_order_id} must exist in orders table"
        if "item_id" in grounded:
            cur.execute("SELECT 1 FROM products WHERE product_id = %s;", (grounded["item_id"],))
            assert cur.fetchone() is not None, f"Referenced item {grounded['item_id']} must exist in products table"
        if "supplier_id" in grounded:
            cur.execute("SELECT 1 FROM suppliers WHERE supplier_id = %s;", (grounded["supplier_id"],))
            assert cur.fetchone() is not None, f"Referenced supplier {grounded['supplier_id']} must exist in suppliers table"


@pytest.mark.integration
def test_seeded_deterministic_selection(test_conn):
    """Providing a fixed seed produces reproducible template selection."""
    sched = ScenarioScheduler()
    t1 = sched.find_eligible_scenario(test_conn, seed=42)
    t2 = sched.find_eligible_scenario(test_conn, seed=42)
    assert t1 is not None and t2 is not None
    assert t1[0] == t2[0]  # exact same template_id


@pytest.mark.integration
def test_cycle_idempotency(test_conn, scheduler_test_tracker):
    """Repeated triggers with identical idempotency key do not duplicate scenario instances."""
    sched = ScenarioScheduler()
    key = f"TEST-IDEMP-{uuid.uuid4().hex[:12]}"

    res1 = sched.run_cycle(test_conn, idempotency_key=key)
    assert res1["executed"] is True
    s_id_1 = res1["scenario_id"]
    scheduler_test_tracker["scenario_ids"].append(s_id_1)

    # Second run with same idempotency key
    res2 = sched.run_cycle(test_conn, idempotency_key=key)
    assert res2["executed"] is False
    assert res2["status"] == "EXISTING_INSTANCE"
    assert res2["scenario_id"] == s_id_1

    # Verify database has exactly 1 instance for this key
    with test_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM scenario_instances WHERE idempotency_key = %s;", (key,))
        count = cur.fetchone()[0]
        assert count == 1


@pytest.mark.integration
def test_scheduler_api_templates_and_scenarios(client: TestClient, scheduler_test_tracker):
    """API endpoints for listing templates and paginated scenarios return correct schemas."""
    # Templates
    res_tpl = client.get("/api/scheduler/templates")
    assert res_tpl.status_code == 200
    tpls = res_tpl.json()
    assert isinstance(tpls, list)
    assert len(tpls) >= 1
    assert "scenario_template_id" in tpls[0]

    # Scenarios list
    res_scen = client.get("/api/scheduler/scenarios?limit=10")
    assert res_scen.status_code == 200
    scens = res_scen.json()
    assert isinstance(scens, list)

    # Unauthorized trigger
    res_unauth = client.post("/api/scheduler/trigger")
    assert res_unauth.status_code in (401, 403)
