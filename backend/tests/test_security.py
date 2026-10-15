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
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
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


def test_anti_forgery_guard_rejects_spoofed_role_headers(client: TestClient):
    """When a client provides a valid key but attempts to spoof an escalated X-User-Role, HTTP 403 is returned."""
    # Viewer credential with forged ADMIN claim
    res1 = client.get(
        "/api/orders/",
        headers={"X-API-Key": "dev-viewer-key", "X-User-Role": "ADMIN"},
    )
    assert res1.status_code == 403
    assert "does not match authenticated role" in res1.json()["detail"].lower()

    # Operator credential with forged ADMIN claim
    res2 = client.post(
        "/api/scheduler/trigger",
        headers={"X-API-Key": "dev-operator-key", "X-User-Role": "ADMIN"},
    )
    assert res2.status_code == 403
    assert "does not match authenticated role" in res2.json()["detail"].lower()

    # Unauthenticated viewer with forged OPERATOR claim
    res3 = client.get(
        "/api/orders/",
        headers={"X-User-Role": "OPERATOR"},
    )
    assert res3.status_code == 403
    assert "does not match authenticated role" in res3.json()["detail"].lower()


def test_unauthenticated_requests_receive_read_only_viewer_role(client: TestClient):
    """Unauthenticated requests default to VIEWER role: read-only access succeeds, mutating calls fail with 403."""
    # Read-only endpoints work for unauthenticated viewers
    res_orders = client.get("/api/orders/?limit=5")
    assert res_orders.status_code == 200

    res_live = client.get("/api/live")
    assert res_live.status_code == 200

    # Mutating / privileged endpoints are rejected
    res_sched = client.post("/api/scheduler/trigger")
    assert res_sched.status_code == 403
    assert "requires at least" in res_sched.json()["detail"].lower()
    assert "operator" in res_sched.json()["detail"].lower()

    res_act = client.post("/api/actions/propose", json={"scenario_id": "00000000-0000-0000-0000-000000000000", "action_type": "DUMMY"})
    assert res_act.status_code == 403
    assert "requires at least" in res_act.json()["detail"].lower()
    assert "operator" in res_act.json()["detail"].lower()


def test_production_mode_fails_closed_when_keys_unconfigured(client: TestClient, monkeypatch):
    """In production mode, if no security keys are configured, the server fails closed with 500."""
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("FINANCE_API_KEY", raising=False)
    monkeypatch.delenv("SUPPLY_CHAIN_API_KEY", raising=False)
    monkeypatch.delenv("OPERATOR_API_KEY", raising=False)
    monkeypatch.delenv("VIEWER_API_KEY", raising=False)

    res = client.get("/api/orders/")
    assert res.status_code == 500
    assert "missing in production" in res.json()["detail"].lower()


def test_api_contract_routes_consistency(client: TestClient):
    """Verify frontend API client contract endpoints exist and return correct shapes."""
    # Liveness check (used by Docker healthcheck & apiClient.checkLive)
    res_live = client.get("/api/live")
    assert res_live.status_code == 200
    assert res_live.json().get("status") in {"healthy", "alive"}

    # Orders summary (used by apiClient.getOrderSummary)
    res_summary = client.get("/api/orders/summary")
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert "total_orders" in summary_data
    assert "processing_count" in summary_data
    assert "completed_count" in summary_data
    assert "exception_count" in summary_data

    # Inventory items alias (used by apiClient.getInventoryItems)
    res_inv = client.get("/api/inventory/items?limit=5")
    assert res_inv.status_code == 200
    assert isinstance(res_inv.json(), list)

    # Audit events alias (used by apiClient.getAuditEvents)
    res_audit = client.get("/api/audit/events?limit=5")
    assert res_audit.status_code == 200
    assert isinstance(res_audit.json(), list)


def test_self_approval_and_amount_limits_enforced(client: TestClient, test_conn):
    """Server-side authorization forbids self-approval and enforces financial spending limits."""
    import uuid
    scenario_id = str(uuid.uuid4())
    action_ids = []

    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenario_instances (
                scenario_id, scenario_template_id, linked_order_id, severity,
                status, scheduled_at, input_overlay, idempotency_key, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, NOW(), NOW());
            """,
            (
                scenario_id,
                "TPL-010",
                "ORD-TEST-SEC",
                "MEDIUM",
                "RUNNING",
                '{"note": "security test"}',
                f"SEC-IDEMP-{scenario_id}",
            ),
        )
    test_conn.commit()

    try:
        # 1. Propose action using dev-finance-key (identity: finance_approver)
        prop_res = client.post(
            "/api/actions/propose",
            headers={"X-API-Key": "dev-finance-key"},
            json={
                "scenario_id": scenario_id,
                "action_type": "CREATE_PURCHASE_ORDER",
                "payload": {
                    "supplier_id": "SUP-001",
                    "item_id": "MAT-IRON",
                    "quantity": 100.0,
                    "estimated_cost": 55000000.0,
                },
            },
        )
        assert prop_res.status_code == 201
        action1_id = prop_res.json()["action_id"]
        action_ids.append(action1_id)

        # Retrieve approval request for action1
        apprs1 = [a for a in client.get("/api/approvals/?status=PENDING").json() if a.get("action_id") == action1_id]
        assert len(apprs1) == 1
        approval1_id = apprs1[0]["approval_id"]

        # Attempt self-approval with dev-finance-key -> MUST FAIL with 403 Forbidden
        dec_self = client.post(
            f"/api/approvals/{approval1_id}/decision",
            headers={"X-API-Key": "dev-finance-key"},
            json={"status": "APPROVED", "reason": "Attempting self-approval"},
        )
        assert dec_self.status_code == 403
        assert "self-approval is prohibited" in dec_self.json()["detail"].lower()

        # Another user with ADMIN role can approve it
        dec_admin = client.post(
            f"/api/approvals/{approval1_id}/decision",
            headers={"X-API-Key": "dev-admin-key"},
            json={"status": "APPROVED", "reason": "Admin approval of coworker action"},
        )
        assert dec_admin.status_code == 200

        # 2. Propose a high-value action (> ₹60M threshold) with dev-operator-key
        prop_high = client.post(
            "/api/actions/propose",
            headers={"X-API-Key": "dev-operator-key"},
            json={
                "scenario_id": scenario_id,
                "action_type": "CREATE_PURCHASE_ORDER",
                "payload": {
                    "supplier_id": "SUP-001",
                    "item_id": "MAT-IRON",
                    "quantity": 100.0,
                    "estimated_cost": 62000000.0,
                },
            },
        )
        assert prop_high.status_code == 201
        action2_id = prop_high.json()["action_id"]
        action_ids.append(action2_id)

        apprs2 = [a for a in client.get("/api/approvals/?status=PENDING").json() if a.get("action_id") == action2_id]
        assert len(apprs2) == 1
        approval2_id = apprs2[0]["approval_id"]

        # Finance approver attempts approval for ₹62M -> exceeds ₹60M limit -> 403 Forbidden
        dec_fin_limit = client.post(
            f"/api/approvals/{approval2_id}/decision",
            headers={"X-API-Key": "dev-finance-key"},
            json={"status": "APPROVED", "reason": "Approving high value order"},
        )
        assert dec_fin_limit.status_code == 403
        assert "exceeds approval limit" in dec_fin_limit.json()["detail"].lower()

        # Admin approves the high value order -> 200 OK
        dec_adm_high = client.post(
            f"/api/approvals/{approval2_id}/decision",
            headers={"X-API-Key": "dev-admin-key"},
            json={"status": "APPROVED", "reason": "Admin authorized high value order"},
        )
        assert dec_adm_high.status_code == 200

    finally:
        # Clean up created test entities in strict reverse dependency order
        with test_conn.cursor() as cur:
            if action_ids:
                cur.execute("DELETE FROM approval_requests WHERE action_id::text = ANY(%s);", (action_ids,))
                cur.execute("DELETE FROM policy_evaluations WHERE action_id::text = ANY(%s);", (action_ids,))
                cur.execute("DELETE FROM action_queue WHERE action_id::text = ANY(%s);", (action_ids,))
            cur.execute("DELETE FROM decisions WHERE scenario_id = %s;", (scenario_id,))
            cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (scenario_id,))
        test_conn.commit()


# ── Phase 3.5 Security Hardening Tests (FIND-06) ───────────────────────────

def test_find06_docker_compose_mandatory_interpolation():
    """FIND-06: docker-compose.yml must not contain predictable default credentials and must use mandatory interpolation."""
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    compose_path = os.path.join(repo_root, "docker-compose.yml")
    assert os.path.isfile(compose_path), "docker-compose.yml must exist at repository root"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Reject hardcoded predictable fallbacks
    assert "prod-admin-secure-key" not in content, "Predictable admin key fallback must not exist in docker-compose.yml"
    assert "enterprise_ai_password" not in content, "Hardcoded database password must not exist in docker-compose.yml"

    # Verify mandatory interpolation syntax ${VAR:?...}
    assert "${POSTGRES_PASSWORD:?" in content, "POSTGRES_PASSWORD must use mandatory interpolation"
    assert "${ADMIN_API_KEY:?" in content, "ADMIN_API_KEY must use mandatory interpolation"
    assert "${FINANCE_API_KEY:?" in content, "FINANCE_API_KEY must use mandatory interpolation"

    # Verify frontend build args do not expose secrets
    frontend_section = content.split("frontend:")[1] if "frontend:" in content else ""
    assert "POSTGRES" not in frontend_section, "Database credentials must not be passed to frontend build"
    assert "API_KEY" not in frontend_section, "Backend API keys must not be passed to frontend build"


def test_find06_production_mode_fails_closed_without_keys(monkeypatch):
    """FIND-06: In production mode, missing server keys trigger HTTP 500/401 and fail closed."""
    from fastapi import HTTPException
    from app.core.security import get_current_user

    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("FINANCE_API_KEY", raising=False)
    monkeypatch.delenv("SUPPLY_CHAIN_API_KEY", raising=False)
    monkeypatch.delenv("OPERATOR_API_KEY", raising=False)
    monkeypatch.delenv("VIEWER_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(x_api_key="any-arbitrary-key")
    assert exc_info.value.status_code == 500
    assert "Authentication configuration missing" in exc_info.value.detail


def test_find06_root_env_example_template():
    """FIND-06: Root .env.example must exist with documented variables and safe placeholders."""
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    example_path = os.path.join(repo_root, ".env.example")
    assert os.path.isfile(example_path), "Root .env.example must exist"

    with open(example_path, "r", encoding="utf-8") as f:
        lines = f.read()

    required_vars = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "APP_ENVIRONMENT",
        "ADMIN_API_KEY",
        "FINANCE_API_KEY",
        "SUPPLY_CHAIN_API_KEY",
        "OPERATOR_API_KEY",
        "VIEWER_API_KEY",
        "SCHEDULER_INTERVAL_SECONDS",
    ]
    for var in required_vars:
        assert f"{var}=" in lines, f"Variable {var} must be documented in .env.example"
