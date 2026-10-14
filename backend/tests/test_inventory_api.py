"""Tests for PostgreSQL-backed Inventory API."""

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
def test_inventory_summary_endpoint(client: TestClient):
    """Verify inventory summary endpoint returns aggregate telemetry."""
    res = client.get("/api/inventory/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_skus"] == 150
    assert summary["total_on_hand_qty"] > 1000000.0
    assert summary["total_available_qty"] > 0.0
    assert summary["normal_count"] == 150


@pytest.mark.integration
def test_list_inventory_live_data(client: TestClient):
    """Verify inventory list endpoint returns real records from PostgreSQL."""
    res = client.get("/api/inventory?limit=10")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) > 0

    first = items[0]
    # Check starter model field compatibility
    assert "id" in first
    assert "name" in first
    assert "quantity" in first
    assert "warehouse_id" in first

    # Check rich database and frontend fields
    assert "inventory_id" in first
    assert "item_id" in first
    assert "product_name" in first
    assert "product_category" in first
    assert "warehouse_name" in first
    assert "on_hand_qty" in first
    assert "reserved_qty" in first
    assert "available_qty" in first
    assert "uom" in first
    assert "stock_signal" in first
    assert "shortage" in first
    assert first["on_hand_qty"] >= first["available_qty"]


@pytest.mark.integration
def test_list_inventory_pagination(client: TestClient):
    """Verify pagination with limit and offset."""
    res_page1 = client.get("/api/inventory?limit=5&offset=0")
    assert res_page1.status_code == 200
    page1 = res_page1.json()
    assert len(page1) == 5

    res_page2 = client.get("/api/inventory?limit=5&offset=5")
    assert res_page2.status_code == 200
    page2 = res_page2.json()
    assert len(page2) == 5

    page1_ids = {i["id"] for i in page1}
    page2_ids = {i["id"] for i in page2}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.integration
def test_list_inventory_warehouse_filter(client: TestClient):
    """Verify filtering by warehouse ID."""
    res = client.get("/api/inventory?warehouse_id=WH-FG-01")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 41
    assert all(i["warehouse_id"] == "WH-FG-01" for i in items)


@pytest.mark.integration
def test_list_inventory_product_filter(client: TestClient):
    """Verify filtering by product/item ID."""
    res = client.get("/api/inventory?product_id=PRD-PLT")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 12
    assert all(i["item_id"] == "PRD-PLT" for i in items)


@pytest.mark.integration
def test_list_inventory_stock_signal_filter(client: TestClient):
    """Verify filtering by stock signal."""
    res = client.get("/api/inventory?status=NORMAL")
    assert res.status_code == 200
    items = res.json()
    assert len(items) > 0
    assert all(i["stock_signal"] == "NORMAL" for i in items)


@pytest.mark.integration
def test_list_inventory_category_filter(client: TestClient):
    """Verify filtering by product category."""
    res = client.get("/api/inventory?category=Finished Steel")
    assert res.status_code == 200
    items = res.json()
    assert len(items) > 0
    assert all(i["product_category"] == "Finished Steel" for i in items)


@pytest.mark.integration
def test_list_inventory_empty_result(client: TestClient):
    """Verify unmatched filters return empty list."""
    res = client.get("/api/inventory?warehouse_id=WH-NONEXISTENT")
    assert res.status_code == 200
    assert res.json() == []


def test_list_inventory_invalid_sort_field_returns_400(client: TestClient):
    """Verify invalid sort_by returns 400 Bad Request."""
    res = client.get("/api/inventory?sort_by=hacked_column")
    assert res.status_code == 400
    assert "Invalid sort_by field" in res.json()["detail"]


def test_list_inventory_invalid_sort_order_returns_400(client: TestClient):
    """Verify invalid sort_order returns 400 Bad Request."""
    res = client.get("/api/inventory?sort_order=backwards")
    assert res.status_code == 400
    assert "Invalid sort_order" in res.json()["detail"]


def test_list_inventory_invalid_stock_signal_returns_400(client: TestClient):
    """Verify invalid stock signal returns 400 Bad Request."""
    res = client.get("/api/inventory?status=UNKNOWN_SIGNAL")
    assert res.status_code == 400
    assert "Invalid stock signal" in res.json()["detail"]


@pytest.mark.integration
def test_list_inventory_parameterized_query_safety(client: TestClient):
    """Verify parameterized query prevents SQL injection."""
    res = client.get("/api/inventory?warehouse_id=' OR '1'='1")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.integration
def test_get_single_inventory_item(client: TestClient):
    """Verify single inventory item retrieval by ID."""
    res = client.get("/api/inventory/INV-0001")
    assert res.status_code == 200
    item = res.json()
    assert item["id"] == "INV-0001"
    assert item["inventory_id"] == "INV-0001"
    assert item["item_id"] == "MAT-COAL"
    assert item["product_name"] == "Coking Coal"
    assert item["warehouse_id"] == "WH-SPARE-01"
    assert item["warehouse_name"] == "Maintenance Spares Store"
    assert item["on_hand_qty"] == 9445.0
    assert item["reserved_qty"] == 1703.0
    assert item["available_qty"] == 7742.0
    assert item["uom"] == "MT"
    assert item["stock_signal"] == "NORMAL"
    assert item["reorder_threshold"] == 744.0


@pytest.mark.integration
def test_get_single_inventory_item_not_found(client: TestClient):
    """Verify non-existent inventory ID returns 404."""
    res = client.get("/api/inventory/INV-NONEXISTENT")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_inventory_db_failure_returns_503(client: TestClient):
    """Verify database exceptions are safely mapped to 503 without leaking details."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("internal database error")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    app.dependency_overrides[get_db] = lambda: mock_conn
    try:
        res = client.get("/api/inventory/")
        assert res.status_code == 503
        assert "Database query failed" in res.json()["detail"]
        assert "internal database error" not in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_non_inventory_endpoints_remain_unchanged(client: TestClient):
    """Verify other endpoints remain fully functional and unchanged."""
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_workflow = client.get("/api/workflow/wf-101")
    assert res_workflow.status_code == 200
    assert res_workflow.json()["status"] == "active"

    res_agents = client.get("/api/agents/")
    assert res_agents.status_code == 200
    assert res_agents.json()["supervisor"] == "idle"

    res_audit = client.get("/api/audit/")
    assert res_audit.status_code == 200
    assert res_audit.json()[0]["blockchain_status"] == "SIMULATED"
