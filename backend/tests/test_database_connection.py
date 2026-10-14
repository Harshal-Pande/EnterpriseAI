"""Tests for FastAPI database connection foundation, readiness, and lifecycle."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import health, orders
from app.db.database import (
    DatabaseConnectionError,
    acquire_connection,
    check_db_readiness,
    close_db_pool,
    get_db,
    get_db_connection,
    get_db_pool,
    init_db_pool,
    release_connection,
    set_db_pool,
)
from app.main import app


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def client() -> TestClient:
    """TestClient instance for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


def test_liveness_endpoint_always_returns_200(client: TestClient):
    """Liveness probe must return 200 regardless of database status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "Enterprise AI Mesh" in data["service"]


def test_readiness_when_db_unavailable(client: TestClient):
    """Readiness probe must return 503 when database is unavailable."""
    # Force pool to None and mock get_db_connection to raise
    set_db_pool(None)
    with patch("app.db.database.check_db_readiness", return_value=(False, "unavailable")):
        res = client.get("/api/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "unavailable"

        # Also test the alias /api/health/ready
        res_alias = client.get("/api/health/ready")
        assert res_alias.status_code == 503


def test_missing_database_url_raises_connection_error():
    """get_db must never silently return None; must raise DatabaseConnectionError."""
    set_db_pool(None)
    with patch("app.db.database.get_database_url", return_value=None):
        with pytest.raises(DatabaseConnectionError) as exc_info:
            next(get_db())
        assert exc_info.value.status_code == 503
        assert "not configured or unavailable" in exc_info.value.detail


def test_pool_exhaustion_raises_connection_error():
    """Pool exhaustion must raise DatabaseConnectionError and not expose pool internals."""
    from psycopg2.pool import PoolError

    mock_pool = MagicMock()
    mock_pool.getconn.side_effect = PoolError("out of connections")
    set_db_pool(mock_pool)

    with pytest.raises(DatabaseConnectionError) as exc_info:
        acquire_connection()
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Database connection pool exhausted"


def test_connection_cleanup_on_successful_request():
    """Connection must be rolled back and returned to pool after successful request."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_pool.getconn.return_value = mock_conn
    set_db_pool(mock_pool)

    test_app = FastAPI()

    @test_app.get("/test-db")
    def test_endpoint(conn=Depends(get_db)):
        assert conn is mock_conn
        return {"result": "success"}

    with TestClient(test_app) as test_client:
        res = test_client.get("/test-db")
        assert res.status_code == 200
        assert res.json() == {"result": "success"}

    mock_conn.rollback.assert_called_once()
    mock_pool.putconn.assert_called_once_with(mock_conn, close=False)


def test_connection_cleanup_on_failed_request():
    """Connection must be rolled back and returned to pool when route raises HTTPException."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_pool.getconn.return_value = mock_conn
    set_db_pool(mock_pool)

    test_app = FastAPI()

    @test_app.get("/test-fail")
    def fail_endpoint(conn=Depends(get_db)):
        raise HTTPException(status_code=400, detail="Invalid payload")

    with TestClient(test_app) as test_client:
        res = test_client.get("/test-fail")
        assert res.status_code == 400

    mock_conn.rollback.assert_called_once()
    mock_pool.putconn.assert_called_once_with(mock_conn, close=False)


def test_connection_cleanup_on_server_error():
    """Connection must be rolled back and returned to pool on unhandled route crash."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_pool.getconn.return_value = mock_conn
    set_db_pool(mock_pool)

    test_app = FastAPI()

    @test_app.get("/test-crash")
    def crash_endpoint(conn=Depends(get_db)):
        raise RuntimeError("Unexpected failure")

    with TestClient(test_app, raise_server_exceptions=False) as test_client:
        res = test_client.get("/test-crash")
        assert res.status_code == 500

    mock_conn.rollback.assert_called_once()
    mock_pool.putconn.assert_called_once_with(mock_conn, close=False)


def test_closed_connection_returned_with_close_flag():
    """If a connection was closed during request, pool.putconn must receive close=True."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = True
    set_db_pool(mock_pool)

    release_connection(mock_conn)
    mock_pool.putconn.assert_called_once_with(mock_conn, close=True)


def test_preservation_of_mock_business_endpoints(client: TestClient):
    """Business endpoints must remain mock-backed and unaffected by DB configuration."""
    res_orders = client.get("/api/orders/")
    assert res_orders.status_code == 200
    assert len(res_orders.json()) > 0
    assert "id" in res_orders.json()[0]

    res_post_order = client.post("/api/orders/", json={"item": "steel"})
    assert res_post_order.status_code == 200
    assert res_post_order.json() == {"status": "created", "order_id": "ORD-1043"}

    res_workflow = client.get("/api/workflow/status")
    assert res_workflow.status_code == 200
    assert res_workflow.json()["current_agent"] == "InventoryAgent"

    res_agents = client.get("/api/agents/")
    assert res_agents.status_code == 200
    assert res_agents.json()["inventory"] == "active"

    res_audit = client.get("/api/audit/")
    assert res_audit.status_code == 200
    assert isinstance(res_audit.json(), list)
    if res_audit.json():
        assert "blockchain_status" in res_audit.json()[0]

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json() == {"message": "Enterprise AI Mesh API is running."}


@pytest.mark.integration
def test_real_postgresql_connection_and_readiness(test_database_url, monkeypatch):
    """Integration test: verify real connection, pool, and SELECT 1 against test database."""
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    pool = init_db_pool(database_url=test_database_url, minconn=1, maxconn=3)
    assert pool is not None

    # Test readiness query
    is_ready, msg = check_db_readiness()
    assert is_ready is True
    assert msg == "connected"

    # Test FastAPI readiness endpoint with live DB
    with TestClient(app) as live_client:
        res = live_client.get("/api/ready")
        assert res.status_code == 200
        assert res.json() == {"status": "ready", "database": "connected"}

        res_alias = live_client.get("/api/health/ready")
        assert res_alias.status_code == 200
        assert res_alias.json() == {"status": "ready", "database": "connected"}

    # Test get_db dependency directly against live DB
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 + 1;")
            assert cur.fetchone()[0] == 2
