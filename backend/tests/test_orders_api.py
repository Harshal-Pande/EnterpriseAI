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


def test_create_order_starter_endpoint_preserved(client: TestClient):
    """Verify POST /api/orders/ remains intact as starter mock implementation."""
    res = client.post("/api/orders/", json={"item": "coils"})
    assert res.status_code == 200
    assert res.json() == {"status": "created", "order_id": "ORD-1043"}
