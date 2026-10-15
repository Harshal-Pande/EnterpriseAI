"""Unit and integration tests for Operational Coherence & Order State Machine (Phase 7)."""

import pytest
from fastapi import HTTPException
from app.services.order_service import transition_order_status
from scripts.consistency_check import run_consistency_checks


@pytest.mark.integration
def test_order_state_machine_legal_and_illegal_transitions(test_conn):
    """Verify order state machine rules, 409 rejections, and terminal states."""
    order_id = "ORD-TEST-LIFECYCLE"
    try:
        with test_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orders (order_id, customer_ref, entity_id, status, priority, currency)
                VALUES (%s, 'CUST-TEST', 'EAS-HQ', 'OPEN', 'HIGH', 'INR')
                ON CONFLICT (order_id) DO UPDATE SET status = 'OPEN';
            """, (order_id,))
            test_conn.commit()

        # 1. Valid transition: OPEN -> IN_PROGRESS
        res1 = transition_order_status(test_conn, order_id, "IN_PROGRESS", reason="Operator started work")
        assert res1["transitioned"] is True
        assert res1["new_status"] == "IN_PROGRESS"

        # 2. Valid transition: IN_PROGRESS -> AT_RISK
        res2 = transition_order_status(test_conn, order_id, "AT_RISK", reason="Supplier delay")
        assert res2["transitioned"] is True
        assert res2["new_status"] == "AT_RISK"

        # 3. Valid transition: AT_RISK -> IN_PROGRESS
        res3 = transition_order_status(test_conn, order_id, "IN_PROGRESS", reason="Mitigation found")
        assert res3["transitioned"] is True
        assert res3["new_status"] == "IN_PROGRESS"

        # 4. Valid transition: IN_PROGRESS -> COMPLETED (no undelivered shipments)
        res4 = transition_order_status(test_conn, order_id, "COMPLETED", reason="Delivered")
        assert res4["transitioned"] is True
        assert res4["new_status"] == "COMPLETED"

        # 5. Illegal transition: COMPLETED -> OPEN (Terminal state) -> 409 Conflict
        with pytest.raises(HTTPException) as exc_info:
            transition_order_status(test_conn, order_id, "OPEN", reason="Reopen attempt")
        assert exc_info.value.status_code == 409
        assert "Illegal order status transition" in exc_info.value.detail
    finally:
        with test_conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE order_id = %s;", (order_id,))
            test_conn.commit()


@pytest.mark.integration
def test_order_cancellation_releases_stock_reservations(test_conn):
    """Cancelling an order automatically releases active stock reservations and restores availability."""
    order_id = "ORD-TEST-RESERVATION-REL"
    res_id = None
    inv_id = None
    try:
        with test_conn.cursor() as cur:
            # Pick an inventory item
            cur.execute("SELECT inventory_id, item_id, warehouse_id, on_hand_qty, reserved_qty, available_qty FROM inventory WHERE available_qty >= 50 LIMIT 1;")
            inv = cur.fetchone()
            inv_id, itm, wh, on_hand, reserved, available = inv[0], inv[1], inv[2], float(inv[3]), float(inv[4]), float(inv[5])

            # Create test order in OPEN status
            cur.execute("""
                INSERT INTO orders (order_id, customer_ref, entity_id, status, priority, currency)
                VALUES (%s, 'CUST-TEST', 'EAS-HQ', 'OPEN', 'MEDIUM', 'INR')
                ON CONFLICT (order_id) DO UPDATE SET status = 'OPEN';
            """, (order_id,))

            # Reserve 25 MT for this order
            import uuid
            res_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO stock_reservations (reservation_id, product_id, warehouse_id, reserved_qty_mt, reference_type, reference_id, status)
                VALUES (%s, %s, %s, 25.0, 'ORDER', %s, 'ACTIVE');
            """, (res_id, itm, wh, order_id))

            cur.execute("""
                UPDATE inventory
                SET reserved_qty = reserved_qty + 25.0, available_qty = available_qty - 25.0
                WHERE inventory_id = %s;
            """, (inv_id,))
            test_conn.commit()

        # Cancel order
        res = transition_order_status(test_conn, order_id, "CANCELLED", reason="Customer cancelled")
        assert res["transitioned"] is True
        assert res["new_status"] == "CANCELLED"
        assert res["released_reservations_count"] >= 1

        # Verify reservation is RELEASED and inventory restored
        with test_conn.cursor() as cur:
            cur.execute("SELECT status FROM stock_reservations WHERE reservation_id = %s;", (res_id,))
            res_status = cur.fetchone()[0]
            assert res_status == "RELEASED"

            cur.execute("SELECT reserved_qty, available_qty FROM inventory WHERE inventory_id = %s;", (inv_id,))
            curr_res, curr_avail = cur.fetchone()
            assert float(curr_res) == reserved
            assert float(curr_avail) == available
    finally:
        with test_conn.cursor() as cur:
            if res_id:
                cur.execute("DELETE FROM inventory_movements WHERE reference_id = %s;", (res_id,))
                cur.execute("DELETE FROM stock_reservations WHERE reservation_id = %s;", (res_id,))
            cur.execute("DELETE FROM orders WHERE order_id = %s;", (order_id,))
            test_conn.commit()


@pytest.mark.integration
def test_cross_domain_consistency_suite(test_conn):
    """Consistency checker verifies zero cross-domain violations."""
    report = run_consistency_checks(test_conn)
    assert report["status"] == "HEALTHY"
    assert report["violations_count"] == 0
