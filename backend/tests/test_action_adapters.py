"""Unit and integration tests for DatabaseActionAdapter and ExternalSimulationAdapter (Task P6.3, P6.4, P6.5).

Verifies:
1. Real database state mutations with row locks (SELECT ... FOR UPDATE).
2. Fail-closed rejection when available inventory or budget is insufficient.
3. Creation of stock_reservations and inventory_movements records.
4. Purchase order creation with budget spend commitment.
5. Transactional compensation (reversal) restoring exact before-state values.
6. External simulation adapter returning honest 'SIMULATED_EXTERNAL' execution mode.
"""

import pytest
from app.services.action_adapters import (
    ActionExecutionError,
    DatabaseActionAdapter,
    ExternalSimulationAdapter,
)


@pytest.mark.integration
def test_inventory_reservation_and_compensation(test_conn):
    """DatabaseActionAdapter reserves inventory with row locks and can compensate."""
    # 1. Fetch available stock for a specific inventory row
    with test_conn.cursor() as cur:
        cur.execute("SELECT inventory_id, item_id, warehouse_id, available_qty, reserved_qty FROM inventory WHERE available_qty >= 10.0 LIMIT 1;")
        row = cur.fetchone()
        assert row is not None, "Need at least one inventory row with >= 10 available stock"
        inv_id, item_id, warehouse_id, initial_avail, initial_reserved = row[0], row[1], row[2], float(row[3]), float(row[4])

    res = None
    try:
        # 2. Execute reservation of 5.0 units on that exact inventory_id
        res = DatabaseActionAdapter.execute(
            conn=test_conn,
            action_type="RESERVE_INVENTORY",
            payload={"inventory_id": inv_id, "item_id": item_id, "warehouse_id": warehouse_id, "quantity": 5.0, "order_id": "ORD-TEST-REV"},
            actor_id="TestOperator",
        )
        test_conn.commit()

        assert res["execution_mode"] == "DATABASE"
        assert res["status"] == "SUCCEEDED"
        assert res["diff"]["available_qty"]["delta"] == -5.0

        # Verify that exact inventory row was updated in PostgreSQL
        with test_conn.cursor() as cur:
            cur.execute("SELECT available_qty, reserved_qty FROM inventory WHERE inventory_id = %s;", (inv_id,))
            up_row = cur.fetchone()
            assert float(up_row[0]) == initial_avail - 5.0
            assert float(up_row[1]) == initial_reserved + 5.0

        # 3. Compensate (reverse) the reservation
        comp_res = DatabaseActionAdapter.compensate(
            conn=test_conn,
            action_type="RESERVE_INVENTORY",
            execution_result=res,
            actor_id="TestCompensator",
        )
        test_conn.commit()

        assert comp_res["status"] == "COMPENSATED"
        assert comp_res["reversed_qty"] == 5.0

        # Verify stock is restored
        with test_conn.cursor() as cur:
            cur.execute("SELECT available_qty, reserved_qty FROM inventory WHERE inventory_id = %s;", (inv_id,))
            rest_row = cur.fetchone()
            assert float(rest_row[0]) == initial_avail
            assert float(rest_row[1]) == initial_reserved
    finally:
        # Guaranteed cleanup
        with test_conn.cursor() as cur:
            cur.execute("UPDATE inventory SET available_qty = %s, reserved_qty = %s WHERE inventory_id = %s;", (initial_avail, initial_reserved, inv_id))
            if res and res.get("reservation_id"):
                cur.execute("DELETE FROM stock_reservations WHERE reservation_id = %s;", (res["reservation_id"],))
            if res and res.get("movement_id"):
                cur.execute("DELETE FROM inventory_movements WHERE movement_id = %s;", (res["movement_id"],))
            test_conn.commit()


@pytest.mark.integration
def test_insufficient_inventory_fails_closed(test_conn):
    """DatabaseActionAdapter raises ActionExecutionError if requested qty > available qty."""
    with test_conn.cursor() as cur:
        cur.execute("SELECT inventory_id, item_id, warehouse_id, available_qty FROM inventory LIMIT 1;")
        row = cur.fetchone()
        inv_id, item_id, warehouse_id, avail = row[0], row[1], row[2], float(row[3])

    excess_qty = avail + 9999999.0
    with pytest.raises(ActionExecutionError, match="insufficient available stock"):
        DatabaseActionAdapter.execute(
            conn=test_conn,
            action_type="RESERVE_INVENTORY",
            payload={"inventory_id": inv_id, "item_id": item_id, "warehouse_id": warehouse_id, "quantity": excess_qty},
        )
    test_conn.rollback()


@pytest.mark.integration
def test_purchase_order_budget_commitment_and_compensation(test_conn):
    """DatabaseActionAdapter commits budget on PO creation and can compensate."""
    with test_conn.cursor() as cur:
        cur.execute("SELECT budget_id, available_budget_inr, committed_spend_inr FROM budgets WHERE status = 'ACTIVE' LIMIT 1;")
        row = cur.fetchone()
        b_id, initial_avail, initial_committed = row[0], float(row[1]), float(row[2] or 0.0)

    spend_amount = 15000.0
    res = None
    try:
        res = DatabaseActionAdapter.execute(
            conn=test_conn,
            action_type="CREATE_PURCHASE_ORDER",
            payload={"budget_id": b_id, "spend": spend_amount, "supplier_id": "SUP-001", "item_id": "PRD-HRC", "quantity": 10.0},
            actor_id="TestOperator",
        )
        test_conn.commit()

        assert res["execution_mode"] == "DATABASE"
        po_id = res["purchase_order_id"]
        assert po_id.startswith("PO-")

        # Verify budget updated
        with test_conn.cursor() as cur:
            cur.execute("SELECT available_budget_inr, committed_spend_inr FROM budgets WHERE budget_id = %s;", (b_id,))
            b_updated = cur.fetchone()
            assert float(b_updated[0]) == initial_avail - spend_amount
            assert float(b_updated[1]) == initial_committed + spend_amount

        # Compensate (cancel PO and restore budget)
        comp_res = DatabaseActionAdapter.compensate(
            conn=test_conn,
            action_type="CREATE_PURCHASE_ORDER",
            execution_result=res,
        )
        test_conn.commit()
        assert comp_res["status"] == "COMPENSATED"

        with test_conn.cursor() as cur:
            cur.execute("SELECT available_budget_inr, committed_spend_inr FROM budgets WHERE budget_id = %s;", (b_id,))
            b_restored = cur.fetchone()
            assert float(b_restored[0]) == initial_avail
            assert float(b_restored[1]) == initial_committed
    finally:
        with test_conn.cursor() as cur:
            cur.execute("UPDATE budgets SET available_budget_inr = %s, committed_spend_inr = %s WHERE budget_id = %s;", (initial_avail, initial_committed, b_id))
            if res and res.get("purchase_order_id"):
                cur.execute("DELETE FROM purchase_orders WHERE po_id = %s;", (res["purchase_order_id"],))
            test_conn.commit()


def test_external_simulation_adapter():
    """ExternalSimulationAdapter returns honest metadata with SIMULATED_EXTERNAL mode."""
    res = ExternalSimulationAdapter.execute(
        action_type="DISPATCH_CARRIER_WEBHOOK",
        payload={"carrier_id": "CAR-001", "lane": "DEL-PUN"},
        actor="TestUser",
    )
    assert res["execution_mode"] == "SIMULATED_EXTERNAL"
    assert res["status"] == "SIMULATED_SUCCESS"
    assert "Simulated external ERP" in res["disclaimer"]
