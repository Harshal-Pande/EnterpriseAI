"""Tests for PostgreSQL-backed Suppliers API endpoints."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, get_db, init_db_pool
from app.main import app


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def client() -> TestClient:
    """TestClient for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_list_suppliers_live_data(client: TestClient, test_database_url: str):
    """Verify list_suppliers returns real records from PostgreSQL seeded database."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/suppliers/")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 8

    # Verify first supplier shape and backward compatibility fields
    sup1 = next((s for s in data if s["supplier_id"] == "SUP-001"), None)
    assert sup1 is not None
    assert sup1["id"] == "SUP-001"
    assert sup1["supplier_id"] == "SUP-001"
    assert sup1["name"] == "Bharat Mineral Logistics (fictional)"
    assert sup1["supplier_name"] == "Bharat Mineral Logistics (fictional)"
    assert sup1["supplier_category"] == "RAW_MATERIAL"
    assert sup1["category"] == "RAW_MATERIAL"
    assert sup1["status"] == "ACTIVE"
    assert sup1["risk_band"] == "LOW"
    assert sup1["historical_on_time_rate"] == 0.96
    assert sup1["reliability_score"] == 96.0
    assert sup1["score"] == 96.0
    assert sup1["default_lead_time_hours"] == 36
    assert sup1["delivery_days"] == 1.5
    assert sup1["deliveryDays"] == 1.5
    assert sup1["contracts_count"] == 1
    assert sup1["offers_count"] == 1
    assert sup1["price_per_unit"] == 6500.0
    assert sup1["pricePerUnit"] == 6500.0
    assert sup1["availability"] == 30000.0


@pytest.mark.integration
def test_list_suppliers_pagination(client: TestClient, test_database_url: str):
    """Verify limit and offset pagination works deterministically."""
    init_db_pool(database_url=test_database_url)

    res_p1 = client.get("/api/suppliers/?limit=3&offset=0&sort_by=supplier_id&sort_order=asc")
    assert res_p1.status_code == 200
    p1 = res_p1.json()
    assert len(p1) == 3

    res_p2 = client.get("/api/suppliers/?limit=3&offset=3&sort_by=supplier_id&sort_order=asc")
    assert res_p2.status_code == 200
    p2 = res_p2.json()
    assert len(p2) == 3

    p1_ids = [s["supplier_id"] for s in p1]
    p2_ids = [s["supplier_id"] for s in p2]
    assert len(set(p1_ids).intersection(set(p2_ids))) == 0


@pytest.mark.integration
def test_list_suppliers_category_filter(client: TestClient, test_database_url: str):
    """Verify filtering by supplier category."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/suppliers/?category=RAW_MATERIAL")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 3
    for s in items:
        assert s["supplier_category"] == "RAW_MATERIAL"


@pytest.mark.integration
def test_list_suppliers_status_filter(client: TestClient, test_database_url: str):
    """Verify filtering by status."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/suppliers/?status=ACTIVE")
    assert res.status_code == 200
    assert len(res.json()) == 8

    res_inactive = client.get("/api/suppliers/?status=INACTIVE")
    assert res_inactive.status_code == 200
    assert len(res_inactive.json()) == 0


@pytest.mark.integration
def test_list_suppliers_risk_band_filter(client: TestClient, test_database_url: str):
    """Verify filtering by risk_band."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/suppliers/?risk_band=HIGH")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["supplier_id"] == "SUP-005"
    assert items[0]["risk_band"] == "HIGH"


@pytest.mark.integration
def test_list_suppliers_empty_result(client: TestClient, test_database_url: str):
    """Verify consistent empty list when filters match no records."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/suppliers/?category=AEROSPACE_NONEXISTENT")
    assert res.status_code == 200
    assert res.json() == []


def test_list_suppliers_invalid_status_returns_400(client: TestClient):
    """Invalid status parameter must return 400 Bad Request."""
    res = client.get("/api/suppliers/?status=BOGUS_STATUS")
    assert res.status_code == 400
    assert "Invalid supplier status" in res.json()["detail"]


def test_list_suppliers_invalid_risk_band_returns_400(client: TestClient):
    """Invalid risk_band parameter must return 400 Bad Request."""
    res = client.get("/api/suppliers/?risk_band=EXTREME")
    assert res.status_code == 400
    assert "Invalid risk_band" in res.json()["detail"]


def test_list_suppliers_invalid_sort_field_returns_400(client: TestClient):
    """Invalid sort_by field must return 400 Bad Request."""
    res = client.get("/api/suppliers/?sort_by=malicious_column")
    assert res.status_code == 400
    assert "Invalid sort_by field" in res.json()["detail"]


def test_list_suppliers_invalid_sort_order_returns_400(client: TestClient):
    """Invalid sort_order must return 400 Bad Request."""
    res = client.get("/api/suppliers/?sort_order=sideways")
    assert res.status_code == 400
    assert "Invalid sort_order" in res.json()["detail"]


@pytest.mark.integration
def test_list_suppliers_parameterized_query_safety(client: TestClient, test_database_url: str):
    """Verify parameterized queries handle SQL injection attempts safely."""
    init_db_pool(database_url=test_database_url)

    injection = "' OR 1=1; DROP TABLE suppliers; --"
    res = client.get(f"/api/suppliers/?category={injection}")
    assert res.status_code == 200
    assert res.json() == []

    # Table must remain intact
    res_after = client.get("/api/suppliers/")
    assert res_after.status_code == 200
    assert len(res_after.json()) == 8


@pytest.mark.integration
def test_get_single_supplier_with_contracts_and_offers(client: TestClient, test_database_url: str):
    """Verify detailed single supplier endpoint returns joined contracts and active offers."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/suppliers/SUP-001")
    assert res.status_code == 200
    data = res.json()
    assert data["supplier_id"] == "SUP-001"
    assert data["name"] == "Bharat Mineral Logistics (fictional)"

    # Verify contracts
    contracts = data.get("contracts")
    assert contracts is not None
    assert len(contracts) == 1
    assert contracts[0]["contract_id"] == "CTR-001"
    assert contracts[0]["contract_category"] == "RAW_MATERIAL"
    assert contracts[0]["contract_limit_inr"] == 100000000.0
    assert contracts[0]["currency"] == "INR"
    assert contracts[0]["owner_department"] == "PROCUREMENT"

    # Verify offers
    offers = data.get("offers")
    assert offers is not None
    assert len(offers) == 1
    assert offers[0]["offer_id"] == "OFR-001"
    assert offers[0]["item_id"] == "MAT-IRON"
    assert offers[0]["unit_price_inr"] == 6500.0
    assert offers[0]["price_uom"] == "INR/MT"
    assert offers[0]["max_available_qty"] == 30000.0


@pytest.mark.integration
def test_get_single_supplier_not_found(client: TestClient, test_database_url: str):
    """Verify 404 returned for missing supplier ID."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/suppliers/SUP-NONEXISTENT")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_suppliers_db_failure_returns_503(client: TestClient):
    """Database connection or query errors must return 503 without leaking SQL."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("psycopg2.OperationalError: server closed")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    app.dependency_overrides[get_db] = lambda: mock_conn
    try:
        res = client.get("/api/suppliers/")
        assert res.status_code == 503
        assert "Database query failed" in res.json()["detail"]
        assert "server closed" not in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
def test_non_supplier_endpoints_remain_unchanged(client: TestClient, test_database_url: str):
    """Verify other endpoints are not broken by the suppliers router addition."""
    init_db_pool(database_url=test_database_url)

    res_health = client.get("/api/health")
    assert res_health.status_code == 200

    res_orders = client.get("/api/orders/?limit=1")
    assert res_orders.status_code == 200

    res_inventory = client.get("/api/inventory/?limit=1")
    assert res_inventory.status_code == 200
