"""Integration tests for Order Lifecycle Pipeline (FIFO Queue, Agent Decisions, Blockchain Blocks, Exceptions)."""

from __future__ import annotations

import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, get_db
from app.main import app
from app.services.lifecycle_queue_service import OrderLifecycleService


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
def lifecycle_cleanup(test_conn):
    created_orders: list[str] = []
    yield created_orders

    try:
        test_conn.rollback()
        with test_conn.cursor() as cur:
            for oid in created_orders:
                cur.execute("DELETE FROM orders_queued WHERE order_id = %s;", (oid,))
                cur.execute("DELETE FROM orders_running WHERE order_id = %s;", (oid,))
                cur.execute("DELETE FROM orders_done WHERE order_id = %s;", (oid,))
                cur.execute("DELETE FROM agent_decision_logs WHERE order_id = %s;", (oid,))
                cur.execute("DELETE FROM blockchain_tx_queue WHERE order_id = %s;", (oid,))
                cur.execute("DELETE FROM operational_exceptions WHERE order_id = %s;", (oid,))
                cur.execute("DELETE FROM order_lines WHERE order_id = %s;", (oid,))
                cur.execute("DELETE FROM orders WHERE order_id = %s;", (oid,))
            test_conn.commit()
    except Exception:
        test_conn.rollback()


def _create_test_order(conn, order_id: str, queue_pos: int, customer: str = "Test Automotive Ltd"):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (
                order_id, customer_ref, entity_id, status, priority,
                currency, external_reference, created_at, updated_at
            ) VALUES (
                %s, %s, 'EAS-EAST', 'OPEN', 'MEDIUM',
                'INR', %s, NOW(), NOW()
            ) ON CONFLICT (order_id) DO NOTHING;
            """,
            (order_id, customer, f"PO-{order_id}"),
        )
        cur.execute(
            """
            INSERT INTO order_lines (
                order_line_id, order_id, product_id, requested_qty, unit_price_inr, uom, created_at
            ) VALUES (
                %s, %s, 'PRD-HRC', 40.0, 72000.0, 'MT', NOW()
            ) ON CONFLICT (order_line_id) DO NOTHING;
            """,
            (f"OL-{order_id}-01", order_id),
        )
        cur.execute(
            """
            INSERT INTO orders_queued (
                queue_id, order_id, customer_name, product_code, quantity_tons, priority, queue_position, scenario_type
            ) VALUES (
                gen_random_uuid(), %s, %s, 'PRD-HRC', 40.0, 'MEDIUM', %s, 'NORMAL'
            ) ON CONFLICT (order_id) DO UPDATE SET queue_position = %s;
            """,
            (order_id, customer, queue_pos, queue_pos),
        )
        conn.commit()


def test_fifo_order_selection_order(test_conn, lifecycle_cleanup):
    """Verify strict FIFO popping: Order with lowest queue_position is popped first."""
    o1 = f"ORD-TEST-FIFO-01-{uuid.uuid4().hex[:6]}"
    o2 = f"ORD-TEST-FIFO-02-{uuid.uuid4().hex[:6]}"
    o3 = f"ORD-TEST-FIFO-03-{uuid.uuid4().hex[:6]}"
    lifecycle_cleanup.extend([o1, o2, o3])

    _create_test_order(test_conn, o1, queue_pos=-30)
    _create_test_order(test_conn, o2, queue_pos=-20)
    _create_test_order(test_conn, o3, queue_pos=-10)

    # Pop 1st: Must be o1
    res1 = OrderLifecycleService.pop_and_execute_order(test_conn)
    assert res1["executed"] is True
    assert res1["order_id"] == o1
    assert res1["status"] == "COMPLETED"

    # Pop 2nd: Must be o2
    res2 = OrderLifecycleService.pop_and_execute_order(test_conn)
    assert res2["executed"] is True
    assert res2["order_id"] == o2
    assert res2["status"] == "COMPLETED"

    # Pop 3rd: Must be o3
    res3 = OrderLifecycleService.pop_and_execute_order(test_conn)
    assert res3["executed"] is True
    assert res3["order_id"] == o3
    assert res3["status"] == "COMPLETED"


def test_order_lifecycle_transitions_and_no_requeue(test_conn, lifecycle_cleanup):
    """Verify Queued -> Running -> Done transition, and that completed orders are NEVER re-queued."""
    order_id = f"ORD-TEST-LC-{uuid.uuid4().hex[:6]}"
    lifecycle_cleanup.append(order_id)

    _create_test_order(test_conn, order_id, queue_pos=-50)

    # Verify present in orders_queued
    with test_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders_queued WHERE order_id = %s;", (order_id,))
        assert cur.fetchone()[0] == 1

    # Execute order
    res = OrderLifecycleService.pop_and_execute_order(test_conn, target_order_id=order_id)
    assert res["executed"] is True
    assert res["status"] == "COMPLETED"

    # Verify order is NO LONGER in orders_queued
    with test_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders_queued WHERE order_id = %s;", (order_id,))
        assert cur.fetchone()[0] == 0

        # Verify order is NO LONGER in orders_running
        cur.execute("SELECT COUNT(*) FROM orders_running WHERE order_id = %s;", (order_id,))
        assert cur.fetchone()[0] == 0

        # Verify order IS in orders_done
        cur.execute("SELECT COUNT(*), outcome_status FROM orders_done WHERE order_id = %s GROUP BY outcome_status;", (order_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 1
        assert row[1] == "COMPLETED"


def test_agent_decisions_persistence_and_blockchain_blocks(test_conn, lifecycle_cleanup):
    """Verify that agent decisions are logged for all 5 specialist agents and mined into a blockchain block."""
    order_id = f"ORD-TEST-DEC-{uuid.uuid4().hex[:6]}"
    lifecycle_cleanup.append(order_id)

    _create_test_order(test_conn, order_id, queue_pos=-40)

    res = OrderLifecycleService.pop_and_execute_order(test_conn, target_order_id=order_id)
    assert res["executed"] is True
    block_num = res["block_number"]
    assert block_num > 0
    assert res["block_hash"].startswith("0x")
    assert res["tx_hash"].startswith("0x")

    # Verify agent decision records in agent_decision_logs
    with test_conn.cursor() as cur:
        cur.execute(
            """
            SELECT agent_name, decision_type, finding, anchored_to_blockchain 
            FROM agent_decision_logs 
            WHERE order_id = %s 
            ORDER BY created_at ASC;
            """,
            (order_id,),
        )
        dec_rows = cur.fetchall()
        assert len(dec_rows) == 5
        agent_names = [r[0] for r in dec_rows]
        assert "Supervisor Agent" in agent_names
        assert "Inventory Agent" in agent_names
        assert "Procurement Agent" in agent_names
        assert "Finance Agent" in agent_names
        assert "Logistics Agent" in agent_names

        for r in dec_rows:
            assert r[3] is True  # anchored_to_blockchain

        # Verify block in blockchain_blocks table
        cur.execute(
            """
            SELECT block_number, block_hash, transaction_count, validator 
            FROM blockchain_blocks 
            WHERE block_number = %s;
            """,
            (block_num,),
        )
        b_row = cur.fetchone()
        assert b_row is not None
        assert b_row[0] == block_num
        assert b_row[2] == 5  # 5 transactions mined


def test_exception_handling_live_hold(test_conn, lifecycle_cleanup):
    """Verify that an exception scenario holds the order in orders_running and creates operational_exceptions."""
    order_id = f"ORD-TEST-EXC-{uuid.uuid4().hex[:6]}"
    lifecycle_cleanup.append(order_id)

    _create_test_order(test_conn, order_id, queue_pos=-35)

    res = OrderLifecycleService.pop_and_execute_order(
        test_conn, target_order_id=order_id, scenario_type="SUPPLIER_UNAVAILABLE"
    )
    assert res["executed"] is True
    assert res["status"] == "EXCEPTION"
    assert res["exception_type"] == "SUPPLIER_UNAVAILABLE"

    # Verify held in orders_running with EXCEPTION status
    with test_conn.cursor() as cur:
        cur.execute(
            "SELECT status, current_stage, last_error FROM orders_running WHERE order_id = %s;",
            (order_id,),
        )
        r_row = cur.fetchone()
        assert r_row is not None
        assert r_row[0] == "EXCEPTION"
        assert r_row[1] == "EXCEPTION"
        assert "supplier" in r_row[2].lower()

        # Verify operational_exceptions entry created
        cur.execute(
            "SELECT severity, exception_type, status FROM operational_exceptions WHERE order_id = %s;",
            (order_id,),
        )
        exc_row = cur.fetchone()
        assert exc_row is not None
        assert exc_row[1] == "SUPPLIER_UNAVAILABLE"
        assert exc_row[2] == "OPEN"


def test_lifecycle_rest_api(test_client, lifecycle_cleanup, test_conn):
    """Verify REST API lifecycle endpoints for queued, running, done, and run-next."""
    order_id = f"ORD-TEST-API-{uuid.uuid4().hex[:6]}"
    lifecycle_cleanup.append(order_id)
    _create_test_order(test_conn, order_id, queue_pos=-60)

    headers = {"X-API-Key": "dev-operator-key"}

    # 1. GET /api/orders/lifecycle/queued
    res_q = test_client.get("/api/orders/lifecycle/queued?limit=10", headers=headers)
    assert res_q.status_code == 200
    queued = res_q.json()
    assert isinstance(queued, list)
    assert any(q["order_id"] == order_id for q in queued)

    # 2. POST /api/orders/lifecycle/run-order/{order_id}
    res_run = test_client.post(f"/api/orders/lifecycle/run-order/{order_id}?scenario=NORMAL", headers=headers)
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["executed"] is True
    assert run_data["order_id"] == order_id
    assert run_data["status"] == "COMPLETED"

    # 3. GET /api/orders/lifecycle/done
    res_done = test_client.get("/api/orders/lifecycle/done?limit=10", headers=headers)
    assert res_done.status_code == 200
    done = res_done.json()
    assert any(d["order_id"] == order_id for d in done)

    # 4. GET /api/orders/lifecycle/decisions
    res_dec = test_client.get(f"/api/orders/lifecycle/decisions?order_id={order_id}", headers=headers)
    assert res_dec.status_code == 200
    decs = res_dec.json()
    assert len(decs) == 5

    # 5. GET /api/orders/lifecycle/blockchain/blocks
    res_blocks = test_client.get("/api/orders/lifecycle/blockchain/blocks?limit=5", headers=headers)
    assert res_blocks.status_code == 200
    blocks = res_blocks.json()
    assert len(blocks) >= 1


def test_concurrent_claims_prevent_duplicate_execution(test_conn, lifecycle_cleanup):
    """Verify that multiple concurrent claims for a single order execute exactly once."""
    import concurrent.futures
    try:
        from db.connection import connect, get_database_url
    except ImportError:
        from backend.db.connection import connect, get_database_url

    order_id = f"ORD-TEST-CONCUR-{uuid.uuid4().hex[:6]}"
    lifecycle_cleanup.append(order_id)
    _create_test_order(test_conn, order_id, queue_pos=-99)

    def _worker_claim():
        conn = connect("TEST_DATABASE_URL")
        try:
            return OrderLifecycleService.pop_and_execute_order(conn, target_order_id=order_id)
        finally:
            conn.close()

    # 4 concurrent threads attempt to claim the exact same order simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_worker_claim) for _ in range(4)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Exactly 1 must have executed, the other 3 must have received executed: False
    executed_count = sum(1 for r in results if r.get("executed") is True)
    assert executed_count == 1

    # Exactly 1 entry in orders_done
    with test_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders_done WHERE order_id = %s;", (order_id,))
        assert cur.fetchone()[0] == 1


def test_polling_is_side_effect_free(test_client):
    """Verify that polling endpoints never create orders, alter queue state, or trigger execution."""
    headers = {"X-API-Key": "dev-operator-key"}

    # Initial snapshot
    q1 = test_client.get("/api/orders/lifecycle/queued", headers=headers).json()
    r1 = test_client.get("/api/orders/lifecycle/running", headers=headers).json()
    d1 = test_client.get("/api/orders/lifecycle/done", headers=headers).json()

    # 10 successive polls
    for _ in range(10):
        test_client.get("/api/orders/lifecycle/queued", headers=headers)
        test_client.get("/api/orders/lifecycle/running", headers=headers)
        test_client.get("/api/orders/lifecycle/done", headers=headers)
        test_client.get("/api/orders/lifecycle/decisions", headers=headers)
        test_client.get("/api/orders/lifecycle/blockchain/blocks", headers=headers)

    # Post-polling snapshot: Must be identical
    q2 = test_client.get("/api/orders/lifecycle/queued", headers=headers).json()
    r2 = test_client.get("/api/orders/lifecycle/running", headers=headers).json()
    d2 = test_client.get("/api/orders/lifecycle/done", headers=headers).json()

    assert len(q1) == len(q2)
    assert len(r1) == len(r2)
    assert len(d1) == len(d2)
