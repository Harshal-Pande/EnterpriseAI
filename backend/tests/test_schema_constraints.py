"""SQL CHECK and foreign-key constraint tests (PostgreSQL integration)."""

import pytest

pytestmark = pytest.mark.integration


def _ensure_schema(monkeypatch, test_database_url):
    from migrate import run

    monkeypatch.setenv("TEST_DATABASE_URL", test_database_url)
    assert run(dry_run=False, env_var="TEST_DATABASE_URL") == 0


def test_invalid_order_status_is_rejected(test_conn, test_database_url, monkeypatch):
    import psycopg2

    _ensure_schema(monkeypatch, test_database_url)
    with test_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO entities (entity_id, entity_name, entity_type, status) "
            "VALUES ('E1', 'Test', 'Plant', 'ACTIVE') "
            "ON CONFLICT DO NOTHING"
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                "INSERT INTO orders (order_id, customer_ref, entity_id, status, priority) "
                "VALUES ('ORD-BAD', 'CUST-1', 'E1', 'INVALID_STATUS', 'LOW')"
            )
    test_conn.rollback()


def test_orphan_shipment_order_is_rejected(test_conn, test_database_url, monkeypatch):
    import psycopg2

    _ensure_schema(monkeypatch, test_database_url)
    with test_conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                "INSERT INTO shipments (shipment_id, order_id, status, risk_flag) "
                "VALUES ('SHP-BAD', 'ORD-DOES-NOT-EXIST', 'PLANNED', 'NORMAL')"
            )
    test_conn.rollback()


def test_negative_available_qty_is_allowed_by_schema(test_conn, test_database_url, monkeypatch):
    """Documented choice: inventory arithmetic is validated in Python, not a CHECK."""
    _ensure_schema(monkeypatch, test_database_url)
    with test_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO entities (entity_id, entity_name, entity_type, status) "
            "VALUES ('E2', 'Test', 'Plant', 'ACTIVE') ON CONFLICT DO NOTHING"
        )
        cur.execute(
            "INSERT INTO products (product_id, product_name, product_category, base_uom, status) "
            "VALUES ('P1', 'Test product', 'Consumable', 'MT', 'ACTIVE') ON CONFLICT DO NOTHING"
        )
        cur.execute(
            "INSERT INTO warehouses (warehouse_id, warehouse_name, entity_id, warehouse_type, status) "
            "VALUES ('W1', 'WH', 'E2', 'RAW_MATERIAL', 'ACTIVE') ON CONFLICT DO NOTHING"
        )
        cur.execute(
            "INSERT INTO inventory (inventory_id, item_id, warehouse_id, on_hand_qty, reserved_qty, "
            "available_qty, uom, stock_signal) "
            "VALUES ('INV-NEG', 'P1', 'W1', 1, 0, -5, 'MT', 'NORMAL')"
        )
    test_conn.rollback()


def test_utilisation_pct_must_be_between_zero_and_one(test_conn, test_database_url, monkeypatch):
    import psycopg2

    _ensure_schema(monkeypatch, test_database_url)
    with test_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO entities (entity_id, entity_name, entity_type, status) "
            "VALUES ('E3', 'Test', 'Plant', 'ACTIVE') ON CONFLICT DO NOTHING"
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                "INSERT INTO production_lines "
                "(production_line_id, line_name, entity_id, process_stage, status, utilisation_pct) "
                "VALUES ('PL-BAD', 'Line', 'E3', 'Steelmaking', 'RUNNING', 1.5)"
            )
    test_conn.rollback()
