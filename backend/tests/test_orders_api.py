"""Tests for PostgreSQL-backed Orders API."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_list_orders_live_data(client: TestClient):
    """Verify orders endpoint returns real data from PostgreSQL."""
    res = client.get("/api/orders?limit=10")
    assert res.status_code == 200
    orders = res.json()
    assert isinstance(orders, list)
    assert len(orders) > 0

    first = orders[0]
    # Check compatibility with existing starter fields
    assert "id" in first
    assert "status" in first
    assert "customer_id" in first
    assert "total_amount" in first

    # Check rich database columns
    assert "order_id" in first
    assert "customer_ref" in first
    assert "priority" in first
    assert "currency" in first
    assert "created_at" in first
    assert first["currency"] == "INR"
    assert first["total_amount"] >= 0


@pytest.mark.integration
def test_list_orders_pagination(client: TestClient):
    """Verify limit and offset pagination."""
    res_page1 = client.get("/api/orders?limit=3&offset=0")
    assert res_page1.status_code == 200
    page1 = res_page1.json()
    assert len(page1) == 3

    res_page2 = client.get("/api/orders?limit=3&offset=3")
    assert res_page2.status_code == 200
    page2 = res_page2.json()
    assert len(page2) == 3

    # Ensure pages do not overlap
    page1_ids = {o["id"] for o in page1}
    page2_ids = {o["id"] for o in page2}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.integration
def test_list_orders_status_filter(client: TestClient):
    """Verify filtering by order status."""
    res = client.get("/api/orders?status=AT_RISK")
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) > 0
    assert all(o["status"] == "AT_RISK" for o in orders)


@pytest.mark.integration
def test_list_orders_priority_filter(client: TestClient):
    """Verify filtering by priority."""
    res = client.get("/api/orders?priority=CRITICAL")
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) > 0
    assert all(o["priority"] == "CRITICAL" for o in orders)


@pytest.mark.integration
def test_list_orders_customer_filter(client: TestClient):
    """Verify filtering by customer reference."""
    res = client.get("/api/orders?customer_ref=CUST-036")
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) > 0
    assert any("CUST-036" in o["customer_ref"] for o in orders)


@pytest.mark.integration
def test_list_orders_empty_result(client: TestClient):
    """Verify empty result when no orders match filter."""
    res = client.get("/api/orders?customer_ref=NONEXISTENT_CUSTOMER_XYZ")
    assert res.status_code == 200
    assert res.json() == []


def test_list_orders_invalid_status_returns_400(client: TestClient):
    """Verify invalid status returns 400 Bad Request."""
    res = client.get("/api/orders?status=INVALID_STATUS")
    assert res.status_code == 400
    assert "Invalid order status" in res.json()["detail"]


def test_list_orders_invalid_priority_returns_400(client: TestClient):
    """Verify invalid priority returns 400 Bad Request."""
    res = client.get("/api/orders?priority=SUPER_HIGH")
    assert res.status_code == 400
    assert "Invalid priority" in res.json()["detail"]


def test_list_orders_invalid_sort_field_returns_400(client: TestClient):
    """Verify invalid sort_by returns 400 Bad Request (SQL injection safe)."""
    res = client.get("/api/orders?sort_by=drop_table")
    assert res.status_code == 400
    assert "Invalid sort_by field" in res.json()["detail"]


def test_list_orders_invalid_sort_order_returns_400(client: TestClient):
    """Verify invalid sort_order returns 400 Bad Request."""
    res = client.get("/api/orders?sort_order=sideways")
    assert res.status_code == 400
    assert "Invalid sort_order" in res.json()["detail"]


@pytest.mark.integration
def test_list_orders_parameterized_query_safety(client: TestClient):
    """Verify query parameters are properly parameterized against SQL injection."""
    res = client.get("/api/orders?customer_ref=' OR '1'='1")
    assert res.status_code == 200
    # Parameterized query treats the string literally; matches 0 records
    assert res.json() == []


@pytest.mark.integration
def test_get_single_order_with_lines(client: TestClient):
    """Verify single order detail endpoint includes constituent lines."""
    res = client.get("/api/orders/ORD-1042")
    assert res.status_code == 200
    order = res.json()
    assert order["id"] == "ORD-1042"
    assert order["customer_ref"] == "CUST-036"
    assert order["status"] == "AT_RISK"
    assert "lines" in order
    assert isinstance(order["lines"], list)
    assert len(order["lines"]) > 0

    first_line = order["lines"][0]
    assert first_line["product_id"] == "PRD-PLT"
    assert first_line["product_name"] == "Steel Plate"
    assert first_line["requested_qty"] == 2200.0
    assert first_line["unit_price_inr"] == 79000.0
    assert first_line["line_total_inr"] == 173800000.0


@pytest.mark.integration
def test_get_single_order_not_found(client: TestClient):
    """Verify requesting non-existent order returns 404."""
    res = client.get("/api/orders/ORD-NONEXISTENT-9999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_orders_db_failure_returns_503(client: TestClient):
    """Verify database exceptions are safely mapped to 503 without leaking details."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("internal database error")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    app.dependency_overrides[get_db] = lambda: mock_conn
    try:
        res = client.get("/api/orders/")
        assert res.status_code == 503
        assert "Database query failed" in res.json()["detail"]
        assert "internal database error" not in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
def test_create_order_success_with_queue(operator_client: TestClient):
    """Verify manual order creation transactionally persists order, lines, and queue entry."""
    req = {
        "customer_ref": "Test Automotive Corp",
        "entity_id": "EAS-HQ",
        "priority": "HIGH",
        "currency": "INR",
        "lines": [
            {
                "product_id": "PRD-HRC",
                "requested_qty": 45.0,
                "unit_price_inr": 72000.0,
                "uom": "MT",
            },
            {
                "product_id": "PRD-CRC",
                "requested_qty": 20.0,
                "unit_price_inr": 84500.0,
                "uom": "MT",
            },
        ],
        "auto_enqueue": True,
    }
    res = operator_client.post("/api/orders/", json=req)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "created"
    assert data["order_id"].startswith("ORD-")
    assert data["queue_position"] is not None
    assert data["queue_position"] > 0
    assert data["enqueued"] is True

    # Verify created order details
    order = data["order"]
    assert order["customer_ref"] == "Test Automotive Corp"
    assert order["entity_id"] == "EAS-HQ"
    assert order["priority"] == "HIGH"
    assert order["line_count"] == 2
    assert len(order["lines"]) == 2
    assert order["total_quantity"] == 65.0
    expected_amount = (45.0 * 72000.0) + (20.0 * 84500.0)
    assert order["total_amount"] == expected_amount

    # Verify order is fetchable via GET /{order_id}
    fetch_res = operator_client.get(f"/api/orders/{data['order_id']}")
    assert fetch_res.status_code == 200
    assert fetch_res.json()["order_id"] == data["order_id"]

    # Clean up created order to maintain test database isolation
    from app.db.database import get_db_connection
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM order_processing_queue WHERE order_id = %s;", (data["order_id"],))
            cur.execute("DELETE FROM order_lines WHERE order_id = %s;", (data["order_id"],))
            cur.execute("DELETE FROM orders WHERE order_id = %s;", (data["order_id"],))
            conn.commit()


@pytest.mark.integration
def test_create_order_invalid_entity_returns_400(operator_client: TestClient):
    """Verify non-existent entity_id returns 400 Bad Request."""
    req = {
        "customer_ref": "Test Corp",
        "entity_id": "NON_EXISTENT_ENTITY",
        "lines": [{"product_id": "PRD-HRC", "requested_qty": 10.0}],
    }
    res = operator_client.post("/api/orders/", json=req)
    assert res.status_code == 400
    assert "Entity 'NON_EXISTENT_ENTITY' does not exist" in res.json()["detail"]


@pytest.mark.integration
def test_create_order_invalid_product_returns_400(operator_client: TestClient):
    """Verify non-existent product_id returns 400 Bad Request."""
    req = {
        "customer_ref": "Test Corp",
        "entity_id": "EAS-HQ",
        "lines": [{"product_id": "PRD-DOES-NOT-EXIST", "requested_qty": 10.0}],
    }
    res = operator_client.post("/api/orders/", json=req)
    assert res.status_code == 400
    assert "Product 'PRD-DOES-NOT-EXIST' in line 1 does not exist" in res.json()["detail"]


@pytest.mark.integration
def test_create_order_invalid_quantity_returns_400(operator_client: TestClient):
    """Verify non-positive quantity returns 422/400 validation error."""
    req = {
        "customer_ref": "Test Corp",
        "entity_id": "EAS-HQ",
        "lines": [{"product_id": "PRD-HRC", "requested_qty": -5.0}],
    }
    res = operator_client.post("/api/orders/", json=req)
    assert res.status_code in (400, 422)


@pytest.mark.integration
def test_get_order_history_capped_at_100(client: TestClient):
    """Verify /api/orders/history enforces the strict 100-record cap."""
    res = client.get("/api/orders/history?limit=100")
    assert res.status_code == 200
    history = res.json()
    assert isinstance(history, list)
    assert len(history) <= 100
    assert all(o["status"] == "COMPLETED" for o in history)


@pytest.mark.integration
def test_get_order_queue_and_status(client: TestClient, test_conn):
    """Verify /api/orders/queue and /api/orders/queue/status endpoints."""
    from scripts.reconcile_order_queue import reconcile_orders_and_queue
    reconcile_orders_and_queue(test_conn)

    # Status endpoint
    s_res = client.get("/api/orders/queue/status")
    assert s_res.status_code == 200
    s_data = s_res.json()
    assert "total_queued" in s_data
    assert "processing_count" in s_data
    assert "completed_count" in s_data
    assert s_data["total_queued"] >= 0

    # Queue list endpoint
    q_res = client.get("/api/orders/queue?status=QUEUED&limit=10")
    assert q_res.status_code == 200
    q_items = q_res.json()
    assert isinstance(q_items, list)
    assert len(q_items) > 0
    first = q_items[0]
    assert "queue_id" in first
    assert "order_id" in first
    assert "queue_position" in first
    assert first["status"] == "QUEUED"
    assert "order" in first
    assert first["order"]["customer_ref"] is not None

