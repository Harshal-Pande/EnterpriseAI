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
    # Force pool to None so get_db_connection raises DatabaseConnectionError
    set_db_pool(None)
    with patch("app.db.database.get_database_url", return_value=None):
        res = client.get("/api/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "not_ready"
        assert "postgres" in data["subsystems"]
        assert data["subsystems"]["postgres"]["state"] == "unavailable"

        # Also test the /api/ready alias
        res_alias = client.get("/api/ready")
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
    """Core API endpoints must be reachable and return expected structure."""
    # Root endpoint returns structured service metadata
    res_root = client.get("/")
    assert res_root.status_code == 200
    root_data = res_root.json()
    assert root_data["service"] == "Enterprise AI Mesh API"
    assert root_data["status"] == "healthy"
    assert isinstance(root_data["endpoints"], list)

    # Liveness probe is always 200
    res_live = client.get("/api/health")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "healthy"

    # Readiness returns structured subsystems (may be 503 if DB not wired in test pool)
    res_ready = client.get("/api/health/ready")
    assert res_ready.status_code in (200, 503)
    ready_data = res_ready.json()
    assert "status" in ready_data
    assert "subsystems" in ready_data


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

    # Test FastAPI readiness endpoint with live DB — now returns structured subsystems
    with TestClient(app) as live_client:
        res = live_client.get("/api/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert "subsystems" in data
        assert data["subsystems"]["postgres"]["state"] == "live"
        assert "data_freshness" in data

        res_alias = live_client.get("/api/ready")
        assert res_alias.status_code == 200
        assert res_alias.json()["status"] == "ready"

    # Test get_db dependency directly against live DB
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 + 1;")
            assert cur.fetchone()[0] == 2
