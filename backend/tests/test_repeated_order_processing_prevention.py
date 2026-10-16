"""Regression and Invariant Tests for Preventing Repeated Order Processing.

Exercises all required invariants from Section 4.3 & 4.5 of Master Implementation Instructions:
1. One logical order submission must not create multiple logical orders merely because a client retries.
2. At most one worker may hold the active claim for a given queue item at a time.
3. A completed queue item must not be picked up as new work.
4. Repeated delivery of the same work item must not repeat non-idempotent business effects.
5. Worker crash / abandoned claim recovery is safe and bounded.
6. Repeated audit anchoring of the same audit record does not create duplicate jobs or reprocess orders.
"""

from __future__ import annotations

import concurrent.futures
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthUser, UserRole
from app.db.database import close_db_pool, get_db
from app.main import app
from app.models.blockchain import AnchorEventRequest
from app.services.action_service import execute_action, propose_action
from app.models.action import ActionProposeRequest
from app.services.blockchain_service import anchor_audit_event
from app.services.lifecycle_queue_service import OrderLifecycleService
from app.services.order_queue_runner import OrderQueueRunner


@pytest.fixture(autouse=True)
def clean_pool_state():
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def test_client(test_conn):
    def _override_get_db():
        yield test_conn

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def order_cleanup(test_conn):
    created_orders: list[str] = []
    created_actions: list[str] = []
    created_events: list[str] = []

    yield created_orders, created_actions, created_events

    try:
        test_conn.rollback()
        with test_conn.cursor() as cur:
            for act_id in created_actions:
                cur.execute("DELETE FROM action_execution_results WHERE action_id = %s;", (act_id,))
                cur.execute("DELETE FROM action_queue WHERE action_id = %s;", (act_id,))
            for evt_id in created_events:
                cur.execute("DELETE FROM blockchain_anchors WHERE event_id_or_batch_id = %s;", (evt_id,))
            for ord_id in created_orders:
                cur.execute("DELETE FROM agent_decision_logs WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM orders_queued WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM orders_running WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM orders_done WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM order_processing_queue WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM operational_exceptions WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM order_lines WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM orders WHERE order_id = %s;", (ord_id,))
                cur.execute("DELETE FROM event_log WHERE entity_id = %s;", (ord_id,))
            test_conn.commit()
    except Exception:
        test_conn.rollback()


def test_order_submission_idempotency_prevents_duplicate_orders(test_client, order_cleanup, test_conn):
    """Invariant 1: Retrying order creation with the same idempotency_key returns existing order."""
    created_orders, _, _ = order_cleanup
    idem_key = f"IDEM-TEST-{uuid.uuid4().hex}"

    payload = {
        "customer_ref": "Tata Motors Commercial",
        "entity_id": "EAS-EAST",
        "priority": "HIGH",
        "currency": "INR",
        "idempotency_key": idem_key,
        "lines": [
            {
                "product_id": "PRD-HRC",
                "requested_qty": 50.0,
                "unit_price_inr": 72000.0,
                "uom": "MT",
            }
        ],
        "auto_enqueue": True,
    }
    headers = {"X-API-Key": "dev-operator-key"}

    # First submission: creates the order
    res1 = test_client.post("/api/orders/", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["status"] == "created"
    order_id = data1["order_id"]
    created_orders.append(order_id)

    # Second submission: exact same payload and idempotency_key (simulating client retry)
    res2 = test_client.post("/api/orders/", json=payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["status"] == "existing"
    assert data2["order_id"] == order_id  # Must return identical order ID!

    # Third submission using HTTP header 'Idempotency-Key' without payload key
    payload_no_key = dict(payload)
    payload_no_key.pop("idempotency_key")
    headers_with_idem = {"X-API-Key": "dev-operator-key", "Idempotency-Key": idem_key}
    res3 = test_client.post("/api/orders/", json=payload_no_key, headers=headers_with_idem)
    assert res3.status_code == 201
    data3 = res3.json()
    assert data3["status"] == "existing"
    assert data3["order_id"] == order_id

    # Verify database has exactly 1 order row with this idempotency key
    with test_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders WHERE idempotency_key = %s;", (idem_key,))
        assert cur.fetchone()[0] == 1


def test_concurrent_workers_claim_same_pending_item(test_conn, order_cleanup):
    """Invariant 2: At most one worker may hold the active claim for a given queue item."""
    created_orders, _, _ = order_cleanup
    test_order_id = f"ORD-CLAIM-{uuid.uuid4().hex[:8]}"
    created_orders.append(test_order_id)

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (order_id, customer_ref, entity_id, status, priority)
            VALUES (%s, 'Tata Motors Commercial', 'EAS-EAST', 'OPEN', 'MEDIUM');
            """,
            (test_order_id,),
        )
        cur.execute(
            """
            INSERT INTO order_processing_queue (queue_id, order_id, queue_position, status, origin)
            VALUES (gen_random_uuid(), %s, -999, 'QUEUED', 'MANUAL');
            """,
            (test_order_id,),
        )
        test_conn.commit()

    runner1 = OrderQueueRunner(worker_id="worker-node-alpha")
    runner2 = OrderQueueRunner(worker_id="worker-node-beta")

    # Worker 1 claims order
    claim1 = runner1.claim_next_order(test_conn)
    assert claim1 is not None
    q_id_1, o_id_1, _ = claim1
    assert o_id_1 == test_order_id

    # Worker 2 attempts claim while Worker 1 has transitioned it to PROCESSING
    claim2 = runner2.claim_next_order(test_conn)
    # Claim 2 cannot claim test_order_id
    if claim2 is not None:
        assert claim2[1] != test_order_id


def test_completed_order_cannot_be_reclaimed_or_reprocessed(test_conn, order_cleanup):
    """Invariant 3: A completed queue item must not be picked up as new work."""
    created_orders, _, _ = order_cleanup
    test_order_id = f"ORD-DONE-{uuid.uuid4().hex[:8]}"
    created_orders.append(test_order_id)

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (order_id, customer_ref, entity_id, status, priority)
            VALUES (%s, 'Tata Motors Commercial', 'EAS-EAST', 'COMPLETED', 'MEDIUM');
            """,
            (test_order_id,),
        )
        # Marked COMPLETED in order_processing_queue
        cur.execute(
            """
            INSERT INTO order_processing_queue (queue_id, order_id, queue_position, status, origin, completed_at)
            VALUES (gen_random_uuid(), %s, -998, 'COMPLETED', 'MANUAL', NOW());
            """,
            (test_order_id,),
        )
        # Marked in orders_done
        cur.execute(
            """
            INSERT INTO orders_done (done_id, order_id, customer_name, product_code, quantity_tons, outcome_status)
            VALUES (gen_random_uuid(), %s, 'Tata Motors Commercial', 'PRD-HRC', 50.0, 'COMPLETED');
            """,
            (test_order_id,),
        )
        test_conn.commit()

    # 1. OrderQueueRunner should not claim it
    runner = OrderQueueRunner(worker_id="worker-verifier")
    claim = runner.claim_next_order(test_conn)
    if claim is not None:
        assert claim[1] != test_order_id

    # 2. OrderLifecycleService target execution should reject it
    res = OrderLifecycleService.pop_and_execute_order(test_conn, target_order_id=test_order_id)
    assert res["executed"] is False
    assert res["status"] == "ALREADY_COMPLETED"


def test_stale_claim_recovery_after_worker_crash(test_conn, order_cleanup):
    """Invariant 11: Crashed worker claim recovery safely resets to QUEUED if attempts < max."""
    created_orders, _, _ = order_cleanup
    test_order_id = f"ORD-CRASH-{uuid.uuid4().hex[:8]}"
    created_orders.append(test_order_id)

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (order_id, customer_ref, entity_id, status, priority)
            VALUES (%s, 'Tata Motors Commercial', 'EAS-EAST', 'IN_PROGRESS', 'HIGH');
            """,
            (test_order_id,),
        )
        # Order stuck in PROCESSING with claimed_at 10 minutes ago
        cur.execute(
            """
            INSERT INTO order_processing_queue (queue_id, order_id, queue_position, status, origin, claimed_at, attempt_count, max_attempts)
            VALUES (gen_random_uuid(), %s, -995, 'PROCESSING', 'MANUAL', NOW() - interval '600 seconds', 1, 3);
            """,
            (test_order_id,),
        )
        test_conn.commit()

    runner = OrderQueueRunner(worker_id="recovery-supervisor")
    recovered = runner.recover_stale_claims(test_conn, timeout_seconds=300)
    assert recovered >= 1

    with test_conn.cursor() as cur:
        cur.execute("SELECT status, claimed_at, attempt_count FROM order_processing_queue WHERE order_id = %s;", (test_order_id,))
        row = cur.fetchone()
        assert row[0] == "QUEUED"
        assert row[1] is None  # Reset claimed_at


def test_stale_claim_recovery_exhausts_at_max_attempts(test_conn, order_cleanup):
    """Invariant 6: Retries are bounded; exhausted attempts become terminal failures."""
    created_orders, _, _ = order_cleanup
    test_order_id = f"ORD-EXHAUST-{uuid.uuid4().hex[:8]}"
    created_orders.append(test_order_id)

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (order_id, customer_ref, entity_id, status, priority)
            VALUES (%s, 'Tata Motors Commercial', 'EAS-EAST', 'IN_PROGRESS', 'HIGH');
            """,
            (test_order_id,),
        )
        # Stuck in PROCESSING with attempt_count == max_attempts (3)
        cur.execute(
            """
            INSERT INTO order_processing_queue (queue_id, order_id, queue_position, status, origin, claimed_at, attempt_count, max_attempts)
            VALUES (gen_random_uuid(), %s, -994, 'PROCESSING', 'MANUAL', NOW() - interval '600 seconds', 3, 3);
            """,
            (test_order_id,),
        )
        test_conn.commit()

    runner = OrderQueueRunner(worker_id="recovery-supervisor")
    recovered = runner.recover_stale_claims(test_conn, timeout_seconds=300)
    assert recovered >= 1

    with test_conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM order_processing_queue WHERE order_id = %s;", (test_order_id,))
        row = cur.fetchone()
        assert row[0] == "FAILED"
        assert "maximum retry attempts exhausted" in row[1]


def test_action_execution_idempotency_prevents_duplicate_effects(test_conn, order_cleanup):
    """Invariant 4: Re-delivering or retrying an executed action returns existing result without re-executing."""
    _, created_actions, _ = order_cleanup
    scen_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenario_instances (
                scenario_id, scenario_template_id, scheduled_at, status, severity, idempotency_key, created_at, updated_at
            )
            VALUES (%s, 'TPL-010', %s, 'RUNNING', 'LOW', %s, %s, %s);
            """,
            (str(scen_id), now, f"SCEN-IDEM-{uuid.uuid4().hex[:8]}", now, now),
        )
        test_conn.commit()

    action_req = ActionProposeRequest(
        scenario_id=str(scen_id),
        action_type="REORDER_STANDARD_STOCK",
        target_entity_id="EAS-EAST",
        payload={"item_id": "PRD-HRC", "quantity": 10.0, "estimated_cost": 250000.0},
        idempotency_key=f"ACT-IDEM-{uuid.uuid4().hex[:8]}",
    )

    action_record = propose_action(test_conn, action_req)
    created_actions.append(action_record.action_id)

    # 1. Execute action first time -> SUCCEEDED
    res1 = execute_action(test_conn, action_record.action_id, caller_id="operator-test")
    assert res1.status == "SUCCEEDED"

    # 2. Execute action second time -> Idempotent response with identical status
    res2 = execute_action(test_conn, action_record.action_id, caller_id="operator-test")
    assert res2.status == "SUCCEEDED"
    assert res2.action_id == res1.action_id


def test_blockchain_anchoring_idempotency(test_conn, order_cleanup):
    """Invariant 9: Repeated audit anchoring does not duplicate records or cause re-execution."""
    _, _, created_events = order_cleanup
    event_id = f"EVT-IDEM-{uuid.uuid4().hex[:8]}"
    created_events.append(event_id)

    anchor_req = AnchorEventRequest(
        event_id=event_id,
        event_type="ORDER_AUDIT",
        payload={"order_id": "ORD-1001", "action": "APPROVAL_GRANTED", "timestamp": "2026-10-16T12:00:00Z"},
        force_simulation=True,
    )

    # First anchor -> truthful status in simulation
    rec1 = anchor_audit_event(test_conn, anchor_req)
    assert rec1.confirmation_status in ("NOT_SUBMITTED", "CONFIRMED", "PENDING")

    # Second anchor with identical event_id and payload -> returns existing record without duplicate DB row
    rec2 = anchor_audit_event(test_conn, anchor_req)
    assert rec2.anchor_id == rec1.anchor_id
    assert rec2.payload_hash == rec1.payload_hash

    # Verify exactly 1 anchor record exists
    with test_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM blockchain_anchors WHERE event_id_or_batch_id = %s;", (event_id,))
        assert cur.fetchone()[0] == 1
