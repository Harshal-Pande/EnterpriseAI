"""Integration tests for Operational Exceptions API and Resolution Lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_order_and_exception():
    """Create a fresh test order and linked operational exception in OPEN status."""
    order_id = f"ORD-EXC-TEST-{uuid.uuid4().hex[:6]}"
    exc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Use get_db generator
    conn_gen = get_db()
    conn = next(conn_gen)
    try:
        with conn.cursor() as cur:
            # Insert test order
            cur.execute(
                """
                INSERT INTO orders (
                    order_id, customer_ref, entity_id, status, priority, currency,
                    created_at, required_delivery_at
                ) VALUES (
                    %s, 'TEST-CUSTOMER-EXC', 'EAS-EAST', 'AT_RISK', 'HIGH', 'INR',
                    %s, %s
                );
                """,
                (order_id, now, now),
            )
            # Insert order line
            cur.execute(
                """
                INSERT INTO order_lines (
                    order_line_id, order_id, product_id,
                    requested_qty, unit_price_inr, uom
                ) VALUES (
                    %s, %s, 'PRD-HRC', 10.0, 50000.0, 'MT'
                );
                """,
                (f"OL-{order_id}-01", order_id),
            )
            # Insert operational exception in OPEN status first (foreign key target)
            cur.execute(
                """
                INSERT INTO operational_exceptions (
                    exception_id, order_id, severity, exception_type, cause,
                    owner_role, status, ai_recommendation, created_at, updated_at
                ) VALUES (
                    %s, %s, 'HIGH', 'STOCK_SHORTFALL', 'Insufficient inventory at EAS-EAST',
                    'OPERATIONS', 'OPEN', '{"action": "REORDER", "recommended_supplier": "SUP-001"}',
                    %s, %s
                );
                """,
                (exc_id, order_id, now, now),
            )
            # Insert order into processing queue in WAITING_EXCEPTION status referencing exception_id
            cur.execute(
                """
                INSERT INTO order_processing_queue (
                    queue_id, order_id, queue_position, status, exception_id, last_error
                ) VALUES (
                    gen_random_uuid(), %s, 999, 'WAITING_EXCEPTION', %s, 'Inventory shortage for PRD-HRC'
                );
                """,
                (order_id, exc_id),
            )
            conn.commit()
        yield order_id, exc_id
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT action_id, approval_id, scenario_id FROM operational_exceptions WHERE exception_id = %s;", (exc_id,))
                r = cur.fetchone()
                act_id = r[0] if r else None
                appr_id = r[1] if r else None
                sc_id = r[2] if r else None
                if appr_id:
                    cur.execute("DELETE FROM approval_requests WHERE approval_id = %s;", (str(appr_id),))
                if act_id:
                    cur.execute("DELETE FROM action_execution_results WHERE action_id = %s;", (str(act_id),))
                    cur.execute("DELETE FROM policy_evaluations WHERE action_id = %s;", (str(act_id),))
                    cur.execute("DELETE FROM action_queue WHERE action_id = %s;", (str(act_id),))
                if sc_id:
                    cur.execute("DELETE FROM decisions WHERE scenario_id = %s;", (str(sc_id),))
                cur.execute("DELETE FROM operational_exceptions WHERE exception_id = %s;", (exc_id,))
                if sc_id:
                    cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (str(sc_id),))
                cur.execute("DELETE FROM order_processing_queue WHERE order_id = %s;", (order_id,))
                cur.execute("DELETE FROM order_lines WHERE order_id = %s;", (order_id,))
                cur.execute("DELETE FROM orders WHERE order_id = %s;", (order_id,))
                cur.execute("DELETE FROM event_log WHERE entity_id = %s;", (order_id,))
                cur.execute("DELETE FROM event_log WHERE entity_id = %s;", (exc_id,))
                conn.commit()
        except Exception:
            pass
        try:
            conn_gen.close()
        except Exception:
            pass


@pytest.mark.integration
def test_list_exceptions(client: TestClient, test_order_and_exception):
    """Verify listing operational exceptions and filtering."""
    order_id, exc_id = test_order_and_exception
    headers = {"X-API-Key": "dev-viewer-key"}

    res = client.get("/api/exceptions/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(e["exception_id"] == exc_id for e in data)

    # Filter by order_id
    res_order = client.get(f"/api/exceptions/?order_id={order_id}", headers=headers)
    assert res_order.status_code == 200
    order_data = res_order.json()
    assert len(order_data) >= 1
    assert order_data[0]["order_id"] == order_id


@pytest.mark.integration
def test_get_exception_detail(client: TestClient, test_order_and_exception):
    """Verify retrieving detailed exception case file."""
    order_id, exc_id = test_order_and_exception
    headers = {"X-API-Key": "dev-viewer-key"}

    res = client.get(f"/api/exceptions/{exc_id}", headers=headers)
    assert res.status_code == 200
    detail = res.json()
    assert detail["exception_id"] == exc_id
    assert detail["order_id"] == order_id
    assert detail["status"] == "OPEN"
    assert detail["order_details"] is not None
    assert detail["order_details"]["order_id"] == order_id


@pytest.mark.integration
def test_exception_full_resolution_lifecycle(client: TestClient, test_order_and_exception):
    """Test full cycle: propose action -> approve (if needed) -> execute -> verify RESOLVED."""
    order_id, exc_id = test_order_and_exception
    operator_headers = {"X-API-Key": "dev-operator-key"}
    admin_headers = {"X-API-Key": "dev-admin-key"}

    # 1. Propose action: CREATE_PURCHASE_ORDER
    prop_payload = {
        "action_type": "CREATE_PURCHASE_ORDER",
        "target_entity_id": "SUP-001",
        "parameters": {
            "supplier_id": "SUP-001",
            "item_id": "MAT-IRON",
            "quantity": 100.0,
            "unit_price": 6500.0,
            "estimated_cost": 650000.0,
        },
        "justification": "Procure replacement inventory for delayed order",
        "notes": "Fast-tracked by operations desk",
    }
    prop_res = client.post(
        f"/api/exceptions/{exc_id}/propose-action",
        json=prop_payload,
        headers=operator_headers,
    )
    assert prop_res.status_code == 200
    prop_data = prop_res.json()
    assert "action_id" in prop_data
    assert prop_data["status"] in {"AWAITING_APPROVAL", "APPROVED"}

    # 2. If AWAITING_APPROVAL, approve with admin key
    if prop_data["status"] == "AWAITING_APPROVAL":
        appr_payload = {
            "decision": "APPROVED",
            "justification": "Approved high-priority material reorder",
        }
        appr_res = client.post(
            f"/api/exceptions/{exc_id}/approve",
            json=appr_payload,
            headers=admin_headers,
        )
        assert appr_res.status_code == 200
        appr_data = appr_res.json()
        assert appr_data["status"] == "APPROVED"

    # 3. Execute approved action
    exec_res = client.post(
        f"/api/exceptions/{exc_id}/execute",
        headers=operator_headers,
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "RESOLVED"
    assert exec_data["order_status"] == "COMPLETED"

    # 4. Verify exception state in DB
    get_res = client.get(f"/api/exceptions/{exc_id}", headers=operator_headers)
    assert get_res.status_code == 200
    resolved_detail = get_res.json()
    assert resolved_detail["status"] == "RESOLVED"
    assert resolved_detail["resolved_at"] is not None


@pytest.mark.integration
def test_exception_resume_order(client: TestClient, test_order_and_exception):
    """Test manual resume path returning order to queue in QUEUED status."""
    order_id, exc_id = test_order_and_exception
    operator_headers = {"X-API-Key": "dev-operator-key"}

    resume_payload = {
        "notes": "Inventory manually reconciled; returning order to queue."
    }
    res = client.post(
        f"/api/exceptions/{exc_id}/resume",
        json=resume_payload,
        headers=operator_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESOLVED"
    assert data["order_status"] == "OPEN"

    # Verify order queue item status is QUEUED
    conn_gen = get_db()
    conn = next(conn_gen)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, exception_id FROM order_processing_queue WHERE order_id = %s;",
                (order_id,),
            )
            q_row = cur.fetchone()
            assert q_row is not None
            assert q_row[0] == "QUEUED"
            assert q_row[1] is None
    finally:
        conn_gen.close()
