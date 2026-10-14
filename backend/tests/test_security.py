"""Security and Authorization Tests (Task 15).

Verifies:
- Role-based authorization boundaries (VIEWER, OPERATOR, APPROVER, ADMIN)
- Domain approval authorization enforcement
- Rejection of unauthorized actions by VIEWER role (HTTP 403)
- Production API key enforcement (HTTP 401)
- Error sanitization preventing credential leakage in messages and traces
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.sanitizer import sanitize_dict, sanitize_error_message
from app.core.security import AuthUser, UserRole, get_current_user, require_role
from app.db.database import close_db_pool, init_db_pool
from app.main import app


@pytest.fixture
def client(test_database_url, monkeypatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    init_db_pool(database_url=test_database_url)
    with TestClient(app) as test_client:
        yield test_client
    close_db_pool()


def test_user_role_hierarchy_and_domain_permissions():
    """Verify role ranking and domain approval permissions."""
    viewer = AuthUser(user_id="viewer1", role=UserRole.VIEWER)
    operator = AuthUser(user_id="op1", role=UserRole.OPERATOR)
    fin_approver = AuthUser(user_id="fin1", role=UserRole.FINANCE_APPROVER)
    admin = AuthUser(user_id="adm1", role=UserRole.ADMIN)

    # Hierarchy ranks
    assert viewer.has_role(UserRole.VIEWER) is True
    assert viewer.has_role(UserRole.OPERATOR) is False

    assert operator.has_role(UserRole.VIEWER) is True
    assert operator.has_role(UserRole.OPERATOR) is True
    assert operator.has_role(UserRole.ADMIN) is False

    assert admin.has_role(UserRole.VIEWER) is True
    assert admin.has_role(UserRole.ADMIN) is True

    # Domain permissions
    assert fin_approver.can_approve_domain("FINANCE") is True
    assert fin_approver.can_approve_domain("LOGISTICS") is False
    assert admin.can_approve_domain("FINANCE") is True
    assert admin.can_approve_domain("ANY_CUSTOM_DOMAIN") is True


def test_viewer_role_is_forbidden_from_triggering_scheduler(client: TestClient):
    """A user with VIEWER role receives HTTP 403 when trying to trigger scheduler."""
    res = client.post("/api/scheduler/trigger", headers={"X-User-Role": "VIEWER", "X-User-Id": "guest_viewer"})
    assert res.status_code == 403
    assert "requires at least" in res.json()["detail"].lower()


def test_viewer_role_is_forbidden_from_executing_actions(client: TestClient):
    """A user with VIEWER role receives HTTP 403 when trying to execute an action."""
    res = client.post("/api/actions/dummy-id/execute", headers={"X-User-Role": "VIEWER", "X-User-Id": "guest_viewer"})
    assert res.status_code == 403
    assert "requires at least" in res.json()["detail"].lower()


def test_production_mode_requires_valid_api_key(client: TestClient, monkeypatch):
    """In production mode, missing or invalid X-API-Key yields HTTP 401."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "super-secret-prod-token")

    # Missing API key
    res_missing = client.post("/api/scheduler/trigger")
    assert res_missing.status_code == 401

    # Invalid API key
    res_bad = client.post("/api/scheduler/trigger", headers={"X-API-Key": "wrong-token"})
    assert res_bad.status_code == 401


def test_error_sanitizer_redacts_credentials():
    """Sanitizer reliably redacts passwords, tokens, and database DSNs."""
    raw_error = "Exception: failed to connect to postgresql://admin:MySecretPass123@db.prod.internal:5432/finance_db"
    clean = sanitize_error_message(raw_error)
    assert "MySecretPass123" not in clean
    assert "***@" in clean

    payload = {
        "order_id": "ORD-101",
        "password": "plain_password",
        "api_key": "secret_key_123",
        "nested": {"token": "bearer_jwt_456", "item": "PRD-01"},
    }
    clean_dict = sanitize_dict(payload)
    assert clean_dict["password"] == "***"
    assert clean_dict["api_key"] == "***"
    assert clean_dict["nested"]["token"] == "***"
    assert clean_dict["nested"]["item"] == "PRD-01"
