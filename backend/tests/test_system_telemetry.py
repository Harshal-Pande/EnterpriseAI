"""Tests for Phase 10 Dedicated UI Telemetry & Aggregate API Endpoints."""

import pytest
from starlette.testclient import TestClient


def test_overview_summary_endpoint(client: TestClient):
    """GET /api/overview/summary returns executive KPI telemetry."""
    resp = client.get("/api/overview/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "orders_in_progress" in data
    assert "awaiting_approvals_count" in data
    assert "audit_events_today" in data
    assert data["source"] == "PostgreSQL"

    # Verify dual mounting under /api/v1
    v1_resp = client.get("/api/v1/overview/summary")
    assert v1_resp.status_code == 200


def test_benchmarks_endpoint(client: TestClient):
    """GET /api/benchmarks returns truthful performance metrics."""
    resp = client.get("/api/benchmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provenance"] == "RUNTIME_CALCULATED"
    assert "metrics" in data
    assert "latencyMs" in data["metrics"]
    assert "processingCostRs" in data["metrics"]


def test_security_status_endpoint(operator_client: TestClient):
    """GET /api/security/status returns caller role and key status."""
    resp = operator_client.get("/api/security/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_mode"] == "API_KEY_RBAC"
    assert "caller_role" in data
    assert "keys_configured" in data


def test_exceptions_queue_endpoint(client: TestClient):
    """GET /api/exceptions returns list of exceptions."""
    resp = client.get("/api/exceptions")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_agents_telemetry_endpoint(client: TestClient):
    """GET /api/agents/telemetry returns agent runtime performance."""
    resp = client.get("/api/agents/telemetry")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert "as_of" in data


def test_system_consistency_endpoint(client: TestClient):
    """GET /api/system/consistency executes cross-domain checks."""
    resp = client.get("/api/system/consistency")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("HEALTHY", "VIOLATIONS_FOUND")
