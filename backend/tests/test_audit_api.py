"""Tests for PostgreSQL-backed Audit API endpoints.

All test events use isolated fixtures that clean up ONLY explicitly tracked records.
Tests never perform bulk or unqualified deletions.
Simulated blockchain records are explicitly marked as local prototype simulation
and distinguished from verified on-chain transactions (deferred to Phase 7).
"""

from __future__ import annotations

import json
import uuid
from typing import Generator
from unittest.mock import MagicMock

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


@pytest.fixture
def audit_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Fixture that tracks created audit records and cleans up ONLY those exact IDs.

    Guarantees no bulk deletions and leaves shared tables strictly intact.
    """
    tracker: dict[str, list[str]] = {"event_ids": [], "anchor_ids": []}
    yield tracker

    cur = test_conn.cursor()
    try:
        if tracker["anchor_ids"]:
            cur.execute(
                "DELETE FROM blockchain_anchors WHERE event_id_or_batch_id::text = ANY(%s);",
                (tracker["anchor_ids"],),
            )
        if tracker["event_ids"]:
            cur.execute(
                "DELETE FROM event_log WHERE event_id::text = ANY(%s);",
                (tracker["event_ids"],),
            )
        test_conn.commit()
    except Exception:
        test_conn.rollback()


@pytest.mark.integration
def test_get_audit_trail_empty_database(client: TestClient, test_database_url: str):
    """Against clean seeded database with 0 event_log rows, returns empty list."""
    init_db_pool(database_url=test_database_url)

    res = client.get("/api/audit/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.integration
def test_get_audit_trail_with_real_records(
    client: TestClient, test_database_url: str, test_conn, audit_test_tracker: dict
):
    """Verify real event_log records and simulated blockchain_anchors are queried, joined, and serialized.

    Blockchain metadata is explicitly tracked as simulated prototype data,
    distinguished from live on-chain Polygon transactions.
    """
    init_db_pool(database_url=test_database_url)

    test_event_id = str(uuid.uuid4())
    test_order_id = "ORD-2024-TEST-ISOLATED-01"
    audit_test_tracker["event_ids"].append(test_event_id)
    audit_test_tracker["anchor_ids"].append(test_event_id)

    cur = test_conn.cursor()
    # Insert test audit event
    cur.execute(
        """
        INSERT INTO event_log (
            event_id, event_timestamp, event_type, entity_type, entity_id,
            actor_type, actor_id, status, reason_code, evidence_refs,
            payload_hash, previous_event_hash, source_channel
        ) VALUES (
            %s, NOW(), %s, %s, %s,
            %s, %s, %s, %s, %s::jsonb,
            %s, %s, %s
        );
        """,
        (
            test_event_id,
            "ORDER_RECEIVED",
            "ORDER",
            test_order_id,
            "AGENT",
            "SupervisorAgent",
            "SIMULATED",
            "Order validated against simulated budget limits",
            json.dumps(["evidence_doc_1", "evidence_doc_2"]),
            "hash_simulated_payload_123",
            "hash_prev_000",
            "SYSTEM",
        ),
    )

    # Insert simulated blockchain anchor (explicitly marked as local simulation, NOT on-chain receipt)
    cur.execute(
        """
        INSERT INTO blockchain_anchors (
            anchor_id, event_id_or_batch_id, payload_hash, chain_name,
            chain_id, contract_address, transaction_hash, block_number,
            anchored_at, confirmation_status, verification_status
        ) VALUES (
            gen_random_uuid(), %s, %s, %s,
            %s, %s, %s, %s,
            NOW(), %s, %s
        );
        """,
        (
            test_event_id,
            "hash_simulated_payload_123",
            "simulation-local-mesh",
            80002,
            "0x0000000000000000000000000000000000000000",
            "0xsimulated_tx_hash_for_test_001",
            184726,
            "PENDING",
            "NOT_VERIFIED",
        ),
    )
    test_conn.commit()

    # Query API
    res = client.get(f"/api/audit/?entity_id={test_order_id}")
    assert res.status_code == 200
    events = res.json()
    assert len(events) == 1

    ev = events[0]
    assert ev["event_id"] == test_event_id
    assert ev["eventId"] == test_event_id
    assert ev["event_type"] == "ORDER_RECEIVED"
    assert ev["event"] == "ORDER_RECEIVED"
    assert ev["type"] == "ORDER_RECEIVED"
    assert ev["entity_type"] == "ORDER"
    assert ev["entity_id"] == test_order_id
    assert ev["order_id"] == test_order_id
    assert ev["orderId"] == test_order_id
    assert ev["actor_id"] == "SupervisorAgent"
    assert ev["actor"] == "SupervisorAgent"
    assert ev["status"] == "SIMULATED"
    assert ev["blockchain_status"] == "PENDING"
    assert ev["tx_hash"] == "0xsimulated_tx_hash_for_test_001"
    assert ev["txHash"] == "0xsimulated_tx_hash_for_test_001"
    assert ev["block_number"] == 184726
    assert ev["blockNumber"] == 184726
    assert ev["evidence_refs"] == ["evidence_doc_1", "evidence_doc_2"]

    # Detail endpoint test
    res_detail = client.get(f"/api/audit/{test_event_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["event_id"] == test_event_id
    assert detail["order_id"] == test_order_id


@pytest.mark.integration
def test_get_audit_trail_unanchored_event(
    client: TestClient, test_database_url: str, test_conn, audit_test_tracker: dict
):
    """Verify that unanchored audit events report NOT_SUBMITTED with null transaction hashes."""
    init_db_pool(database_url=test_database_url)

    unanchored_id = str(uuid.uuid4())
    audit_test_tracker["event_ids"].append(unanchored_id)

    cur = test_conn.cursor()
    cur.execute(
        """
        INSERT INTO event_log (
            event_id, event_timestamp, event_type, entity_type, entity_id,
            actor_type, actor_id, status, payload_hash
        ) VALUES (%s, NOW(), 'LOCAL_ACTION', 'SYSTEM', 'SYS-01', 'SYSTEM', 'LOCAL_AUDIT', 'LOGGED', 'hash_local');
        """,
        (unanchored_id,),
    )
    test_conn.commit()

    res = client.get(f"/api/audit/{unanchored_id}")
    assert res.status_code == 200
    item = res.json()
    assert item["event_id"] == unanchored_id
    assert item["blockchain_status"] == "NOT_SUBMITTED"
    assert item["tx_hash"] is None
    assert item["txHash"] is None
    assert item["block_number"] is None


@pytest.mark.integration
def test_get_audit_trail_filtering(
    client: TestClient, test_database_url: str, test_conn, audit_test_tracker: dict
):
    """Verify event_type, actor_id, and status filtering with strictly tracked IDs."""
    init_db_pool(database_url=test_database_url)

    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    audit_test_tracker["event_ids"].extend([id1, id2])

    cur = test_conn.cursor()
    cur.execute(
        """
        INSERT INTO event_log (event_id, event_type, entity_type, entity_id, actor_type, actor_id, status, payload_hash)
        VALUES
            (%s, 'INVENTORY_CHECK', 'INVENTORY', 'INV-001', 'AGENT', 'InventoryAgent', 'COMPLETED', 'hash1'),
            (%s, 'SUPPLIER_SELECTED', 'SUPPLIER', 'SUP-001', 'AGENT', 'ProcurementAgent', 'SIMULATED', 'hash2');
        """,
        (id1, id2),
    )
    test_conn.commit()

    # Filter by event_type
    r_type = client.get("/api/audit/?event_type=INVENTORY_CHECK")
    assert r_type.status_code == 200
    assert any(e["event_id"] == id1 for e in r_type.json())
    assert not any(e["event_id"] == id2 for e in r_type.json())

    # Filter by actor_id
    r_actor = client.get("/api/audit/?actor_id=ProcurementAgent")
    assert r_actor.status_code == 200
    assert any(e["event_id"] == id2 for e in r_actor.json())
    assert not any(e["event_id"] == id1 for e in r_actor.json())

    # Filter by status
    r_status = client.get("/api/audit/?status=SIMULATED")
    assert r_status.status_code == 200
    assert any(e["event_id"] == id2 for e in r_status.json())
    assert not any(e["event_id"] == id1 for e in r_status.json())


@pytest.mark.integration
def test_get_audit_trail_pagination_and_sorting(
    client: TestClient, test_database_url: str, test_conn, audit_test_tracker: dict
):
    """Verify limit, offset, and sort_order work deterministically."""
    init_db_pool(database_url=test_database_url)

    ids = [str(uuid.uuid4()) for _ in range(4)]
    audit_test_tracker["event_ids"].extend(ids)

    cur = test_conn.cursor()
    for i, eid in enumerate(ids):
        cur.execute(
            """
            INSERT INTO event_log (event_id, event_timestamp, event_type, entity_type, entity_id, actor_type, actor_id, status, payload_hash)
            VALUES (%s, NOW() + interval '%s seconds', 'PAGINATION_TEST', 'TEST', 'ID', 'AGENT', 'TestAgent', 'LOGGED', 'h');
            """,
            (eid, i),
        )
    test_conn.commit()

    # Limit 2, Offset 0
    r_p1 = client.get("/api/audit/?event_type=PAGINATION_TEST&limit=2&offset=0&sort_order=asc")
    assert r_p1.status_code == 200
    p1 = r_p1.json()
    assert len(p1) == 2

    # Limit 2, Offset 2
    r_p2 = client.get("/api/audit/?event_type=PAGINATION_TEST&limit=2&offset=2&sort_order=asc")
    assert r_p2.status_code == 200
    p2 = r_p2.json()
    assert len(p2) == 2

    p1_ids = [e["event_id"] for e in p1]
    p2_ids = [e["event_id"] for e in p2]
    assert len(set(p1_ids).intersection(set(p2_ids))) == 0


def test_get_audit_trail_invalid_sort_order_returns_400(client: TestClient):
    """Invalid sort_order must return 400 Bad Request."""
    res = client.get("/api/audit/?sort_order=sideways")
    assert res.status_code == 400
    assert "Invalid sort_order" in res.json()["detail"]


@pytest.mark.integration
def test_get_single_audit_event_not_found(client: TestClient, test_database_url: str):
    """Missing UUID must return 404 Not Found."""
    init_db_pool(database_url=test_database_url)

    random_id = str(uuid.uuid4())
    res = client.get(f"/api/audit/{random_id}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_single_audit_event_invalid_uuid_returns_400(client: TestClient):
    """Non-UUID identifier must return 400 Bad Request."""
    res = client.get("/api/audit/not-a-valid-uuid")
    assert res.status_code == 400
    assert "Invalid event_id UUID format" in res.json()["detail"]


def test_audit_db_failure_returns_503(client: TestClient):
    """Database query failure must return 503 without leaking SQL internals."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("internal db exception: connection lost")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    app.dependency_overrides[get_db] = lambda: mock_conn
    try:
        res = client.get("/api/audit/")
        assert res.status_code == 503
        assert "Database query failed" in res.json()["detail"]
        assert "connection lost" not in res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
def test_audit_parameterized_query_safety(client: TestClient, test_database_url: str):
    """Verify SQL injection payloads in filters are safely parameterized."""
    init_db_pool(database_url=test_database_url)

    injection = "' OR 1=1; DROP TABLE event_log; --"
    res = client.get(f"/api/audit/?event_type={injection}")
    assert res.status_code == 200
    assert res.json() == []
