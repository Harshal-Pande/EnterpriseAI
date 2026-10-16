"""Tests for Phase 3: Order Queue Runner service and API controls."""

from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.llm_provider import SimulationProvider
from app.core.security import AuthUser, UserRole
from app.db.database import close_db_pool, get_db
from app.main import app
from app.services.order_queue_runner import (
    OrderQueueRunner,
    default_order_queue_runner,
    get_queue_interval_seconds,
    is_queue_auto_replenish,
    replenish_one_order,
)


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def test_client(test_conn):
    """FastAPI TestClient with overridden database connection and operator role."""
    def _override_get_db():
        yield test_conn

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def runner_cleanup(test_conn):
    """Track and clean up any orders, queue items, or exceptions created during runner tests."""
    created_orders: list[str] = []
    created_exceptions: list[uuid.UUID] = []

    yield created_orders, created_exceptions

    try:
        test_conn.rollback()
        with test_conn.cursor() as cur:
            # Release any lease locks on order-queue-runner
            cur.execute(
                """
                UPDATE scheduler_state
                SET locked_by = NULL, lease_expires_at = NULL, enabled = TRUE, last_status = 'IDLE'
                WHERE scheduler_name = 'order-queue-runner';
                """
            )
            for exc_id in created_exceptions:
                cur.execute("DELETE FROM operational_exceptions WHERE exception_id = %s;", (exc_id,))
            for ord_id in created_orders:
                cur.execute("DELETE FROM blockchain_anchors WHERE event_id_or_batch_id LIKE %s;", (f"%{ord_id}%",))
                cur.execute("DELETE FROM orders_queued WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM orders_running WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM orders_done WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM agent_decision_logs WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM blockchain_tx_queue WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM order_processing_queue WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM order_lines WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM orders WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM event_log WHERE entity_id = %s;", (ord_id,))
            test_conn.commit()
    except Exception:
        test_conn.rollback()


def test_runner_configuration_and_env(monkeypatch):
    """Verify runner configuration helpers honor environment variables with bounds checking."""
    monkeypatch.setenv("ORDER_QUEUE_INTERVAL_SECONDS", "120")
    assert get_queue_interval_seconds() == 120

    monkeypatch.setenv("ORDER_QUEUE_INTERVAL_SECONDS", "invalid")
    assert get_queue_interval_seconds() == 300

    monkeypatch.setenv("ORDER_QUEUE_AUTO_REPLENISH", "false")
    assert is_queue_auto_replenish() is False

    monkeypatch.setenv("ORDER_QUEUE_AUTO_REPLENISH", "true")
    assert is_queue_auto_replenish() is True


def test_runner_status_query(test_conn):
    """Verify get_status returns complete observable state and metrics."""
    runner = OrderQueueRunner(worker_id="test-status-worker")
    status = runner.get_status(test_conn)

    assert status["scheduler_name"] == "order-queue-runner"
    assert "runner_enabled" in status
    assert "runner_status" in status
    assert "runner_interval_seconds" in status
    assert "total_queued" in status
    assert "processing_count" in status
    assert "waiting_exception_count" in status
    assert "completed_count" in status
    assert "total_orders_tracked" in status
    assert "is_locked" in status


def test_runner_pause_and_resume(test_conn):
    """Verify pause and resume successfully toggle scheduler_state enabled flag."""
    runner = OrderQueueRunner(worker_id="test-pause-worker")

    runner.pause(test_conn)
    st_paused = runner.get_status(test_conn)
    assert st_paused["runner_enabled"] is False
    assert st_paused["runner_status"] == "PAUSED"

    runner.resume(test_conn)
    st_resumed = runner.get_status(test_conn)
    assert st_resumed["runner_enabled"] is True
    assert st_resumed["runner_status"] in ("RUNNING", "IDLE")


def test_runner_lease_locking_and_mutual_exclusion(test_conn):
    """Verify lease lock prevents two concurrent runners from claiming simultaneously."""
    runner1 = OrderQueueRunner(worker_id="runner-worker-1")
    runner2 = OrderQueueRunner(worker_id="runner-worker-2")

    # Worker 1 acquires lease
    acquired1, interval1 = runner1.acquire_lease(test_conn, lease_seconds=10)
    assert acquired1 is True

    # Worker 2 attempts to acquire lease -> must be denied
    acquired2, _ = runner2.acquire_lease(test_conn, lease_seconds=10)
    assert acquired2 is False

    # Worker 1 releases lease
    runner1.release_lease(test_conn, outcome_status="COMPLETED")

    # Worker 2 can now acquire lease
    acquired2_after, _ = runner2.acquire_lease(test_conn, lease_seconds=10)
    assert acquired2_after is True
    runner2.release_lease(test_conn, outcome_status="COMPLETED")


def test_replenish_one_order_creates_valid_record(test_conn, runner_cleanup):
    """Verify replenish_one_order creates compliant order, lines, and queued queue item."""
    created_orders, _ = runner_cleanup

    new_order_id = replenish_one_order(test_conn)
    test_conn.commit()
    created_orders.append(new_order_id)

    assert new_order_id.startswith("ORD-")

    with test_conn.cursor() as cur:
        # Check order
        cur.execute("SELECT status, customer_ref, entity_id FROM orders WHERE order_id = %s;", (new_order_id,))
        o_row = cur.fetchone()
        assert o_row is not None
        assert o_row[0] == "OPEN"
        assert len(o_row[1]) > 0
        assert o_row[2] in ("EAS-EAST", "EAS-WEST", "EAS-PORT", "EAS-HQ")

        # Check queue
        cur.execute("SELECT status, origin, queue_position FROM order_processing_queue WHERE order_id = %s;", (new_order_id,))
        q_row = cur.fetchone()
        assert q_row is not None
        assert q_row[0] == "QUEUED"
        assert q_row[1] == "REPLENISHMENT"
        assert q_row[2] > 0

        # Check order_lines
        cur.execute("SELECT COUNT(*) FROM order_lines WHERE order_id = %s;", (new_order_id,))
        assert cur.fetchone()[0] >= 1


def test_runner_process_next_order_clean_execution(test_conn, runner_cleanup):
    """Verify process_next_order cleanly completes an eligible queued order with SimulationProvider."""
    created_orders, created_exceptions = runner_cleanup

    # Seed a dedicated test order in queue to avoid altering ORD-1042/1043
    test_order_id = f"ORD-TEST-{uuid.uuid4().hex[:8]}"
    created_orders.append(test_order_id)

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (
                order_id, customer_ref, entity_id, status, priority,
                currency, external_reference,
                required_delivery_at, created_at, updated_at
            ) VALUES (
                %s, 'Tata Motors Commercial', 'EAS-EAST', 'OPEN', 'MEDIUM',
                'INR', 'EXT-9999',
                NOW() + interval '7 days', NOW(), NOW()
            );
            """,
            (test_order_id,),
        )
        cur.execute(
            """
            INSERT INTO order_lines (
                order_line_id, order_id, product_id, requested_qty, unit_price_inr, uom, created_at
            ) VALUES (
                'OL-TEST-9999-01', %s, 'PRD-HRC', 10.0, 50000.0, 'MT', NOW()
            );
            """,
            (test_order_id,),
        )
        # Position 0 ensures it is claimed first
        cur.execute(
            """
            INSERT INTO order_processing_queue (
                queue_id, order_id, queue_position, status, origin
            ) VALUES (
                gen_random_uuid(), %s, -999, 'QUEUED', 'SYSTEM'
            );
            """,
            (test_order_id,),
        )
        test_conn.commit()

    runner = OrderQueueRunner(worker_id="test-clean-worker")
    sim_provider = SimulationProvider()

    result = runner.process_next_order(test_conn, force=True, llm_provider=sim_provider)
    assert result["executed"] is True
    assert result["order_id"] == test_order_id
    assert result["status"] == "COMPLETED"

    if result.get("replenished_order_id"):
        created_orders.append(result["replenished_order_id"])

    # Verify orders table updated to COMPLETED
    with test_conn.cursor() as cur:
        cur.execute("SELECT status FROM orders WHERE order_id = %s;", (test_order_id,))
        assert cur.fetchone()[0] == "COMPLETED"

        cur.execute("SELECT status, completed_at FROM order_processing_queue WHERE order_id = %s;", (test_order_id,))
        q_row = cur.fetchone()
        assert q_row[0] == "COMPLETED"
        assert q_row[1] is not None


def test_runner_api_endpoints_integration(test_client, runner_cleanup, monkeypatch):
    """Verify REST API runner control endpoints with role authentication."""
    headers = {"X-API-Key": "dev-operator-key"}

    # 1. GET /api/orders/queue/status
    res = test_client.get("/api/orders/queue/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_queued" in data
    assert "runner_status" in data

    # 2. GET /api/orders/queue/runner/status
    res = test_client.get("/api/orders/queue/runner/status", headers=headers)
    assert res.status_code == 200
    r_data = res.json()
    assert r_data["scheduler_name"] == "order-queue-runner"

    # 3. POST /api/orders/queue/runner/pause
    res = test_client.post("/api/orders/queue/runner/pause", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "PAUSED"

    # 4. POST /api/orders/queue/runner/resume
    res = test_client.post("/api/orders/queue/runner/resume", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"

    # 5. POST /api/orders/queue/runner/stop
    res = test_client.post("/api/orders/queue/runner/stop", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "STOPPED"


def test_runner_process_next_order_exception_gate(test_conn, runner_cleanup, monkeypatch):
    """Verify that when an order encounters an approval gate or policy breach, it transitions to WAITING_EXCEPTION and creates operational_exceptions."""
    from unittest.mock import MagicMock
    from app.orchestration.governed import OrchestrationResult

    created_orders, created_exceptions = runner_cleanup
    test_order_id = f"ORD-TEST-EXC-{uuid.uuid4().hex[:8]}"
    created_orders.append(test_order_id)

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (
                order_id, customer_ref, entity_id, status, priority,
                currency, external_reference,
                required_delivery_at, created_at, updated_at
            ) VALUES (
                %s, 'Tata Motors Commercial', 'EAS-EAST', 'OPEN', 'CRITICAL',
                'INR', 'EXT-EXC-01',
                NOW() + interval '3 days', NOW(), NOW()
            );
            """,
            (test_order_id,),
        )
        cur.execute(
            """
            INSERT INTO order_lines (
                order_line_id, order_id, product_id, requested_qty, unit_price_inr, uom, created_at
            ) VALUES (
                %s, %s, 'PRD-HRC', 80.0, 50000.0, 'MT', NOW()
            );
            """,
            (f"OL-{test_order_id}-01", test_order_id),
        )
        cur.execute(
            """
            INSERT INTO order_processing_queue (
                queue_id, order_id, queue_position, status, origin
            ) VALUES (
                gen_random_uuid(), %s, -999, 'QUEUED', 'SYSTEM'
            );
            """,
            (test_order_id,),
        )
        test_conn.commit()

    # Mock GovernedOrchestrator.execute to simulate policy breach
    mock_result = OrchestrationResult(
        correlation_id=str(uuid.uuid4()),
        workflow_id="wf-mock-exc",
        scenario_id="scen-mock-exc",
        order_id=test_order_id,
        status="AWAITING_APPROVAL",
        error="Financial authorization required: commitment exceeds operational limit.",
    )
    mock_result.governance = {"policy_rejected": True}

    monkeypatch.setattr(
        "app.services.order_queue_runner.GovernedOrchestrator.execute",
        MagicMock(return_value=mock_result),
    )

    runner = OrderQueueRunner(worker_id="test-exc-worker")
    res = runner.process_next_order(test_conn, force=True)

    assert res["executed"] is True
    assert res["status"] == "WAITING_EXCEPTION"
    assert res["order_id"] == test_order_id
    assert res["exception_id"] is not None

    created_exceptions.append(uuid.UUID(res["exception_id"]))
    if res.get("replenished_order_id"):
        created_orders.append(res["replenished_order_id"])

    with test_conn.cursor() as cur:
        # Check order updated to AT_RISK
        cur.execute("SELECT status FROM orders WHERE order_id = %s;", (test_order_id,))
        assert cur.fetchone()[0] == "AT_RISK"

        # Check queue updated to WAITING_EXCEPTION with exception_id
        cur.execute("SELECT status, exception_id, last_error FROM order_processing_queue WHERE order_id = %s;", (test_order_id,))
        q_row = cur.fetchone()
        assert q_row[0] == "WAITING_EXCEPTION"
        assert str(q_row[1]) == res["exception_id"]
        assert "Financial authorization required" in q_row[2]

        # Check operational_exceptions record
        cur.execute("SELECT status, exception_type, severity, cause FROM operational_exceptions WHERE exception_id = %s;", (res["exception_id"],))
        exc_row = cur.fetchone()
        assert exc_row is not None
        assert exc_row[0] == "OPEN"
        assert exc_row[1] == "BUDGET_BREACH"
        assert exc_row[2] == "CRITICAL"
        assert "Financial authorization required" in exc_row[3]

