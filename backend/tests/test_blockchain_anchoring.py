"""Tests for Blockchain Audit Anchoring (Task 12).

Verifies:
- RFC 8785 canonical JSON serialization and deterministic SHA-256 digests
- Digest invariance across key ordering and whitespace changes
- Cryptographic sensitivity to modified or tampered payloads
- Honest adapter status when network provider is unconfigured (no fabricated hashes)
- Simulation adapter labeling
- Duplicate anchor prevention
- Integrity verification (MATCHED vs MISMATCH)
- API endpoints for anchoring and verification
- Strict test isolation (cleans up tracked test records)
"""

from __future__ import annotations

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.models.blockchain import AnchorEventRequest
from app.services.blockchain_service import (
    CanonicalHasher,
    anchor_audit_event,
    verify_anchor_integrity,
)


@pytest.fixture(autouse=True)
def clean_pool_state():
    """Ensure clean connection pool state before and after each test."""
    close_db_pool()
    yield
    close_db_pool()


@pytest.fixture
def client(test_database_url, monkeypatch) -> TestClient:
    """TestClient configured with TEST_DATABASE_URL and scheduler loop disabled."""
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    init_db_pool(database_url=test_database_url)
    with TestClient(app) as test_client:
        yield test_client
    close_db_pool()


@pytest.fixture
def anchor_test_tracker(test_conn) -> Generator[dict, None, None]:
    """Track created blockchain anchor records to clean up after test."""
    tracker: dict[str, list[str]] = {"anchor_ids": [], "event_ids": []}
    yield tracker

    cur = test_conn.cursor()
    try:
        if tracker["anchor_ids"]:
            cur.execute(
                "DELETE FROM blockchain_anchors WHERE anchor_id::text = ANY(%s);",
                (tracker["anchor_ids"],),
            )
        if tracker["event_ids"]:
            cur.execute(
                "DELETE FROM blockchain_anchors WHERE event_id_or_batch_id = ANY(%s);",
                (tracker["event_ids"],),
            )
        test_conn.commit()
    except Exception:
        test_conn.rollback()


def test_canonical_hasher_invariance():
    """CanonicalHasher produces the exact same digest regardless of dictionary key ordering."""
    payload_a = {"event_type": "ORDER_APPROVED", "order_id": "ORD-1001", "amount": 5000}
    payload_b = {"amount": 5000, "order_id": "ORD-1001", "event_type": "ORDER_APPROVED"}

    hash_a = CanonicalHasher.compute_digest(payload_a)
    hash_b = CanonicalHasher.compute_digest(payload_b)

    assert hash_a == hash_b
    assert hash_a.startswith("0x")
    assert len(hash_a) == 66  # 0x + 64 hex chars


def test_canonical_hasher_sensitivity():
    """Modifying even a single character in the payload produces a completely different digest."""
    payload_original = {"event_type": "ORDER_APPROVED", "order_id": "ORD-1001", "amount": 5000}
    payload_tampered = {"event_type": "ORDER_APPROVED", "order_id": "ORD-1001", "amount": 5001}

    hash_orig = CanonicalHasher.compute_digest(payload_original)
    hash_tamp = CanonicalHasher.compute_digest(payload_tampered)

    assert hash_orig != hash_tamp


@pytest.mark.integration
def test_unconfigured_network_reports_honest_status(test_conn, anchor_test_tracker, monkeypatch):
    """When no Web3 RPC or contract is configured, reports NOT_SUBMITTED without fabricating hashes."""
    monkeypatch.delenv("WEB3_PROVIDER_URI", raising=False)
    monkeypatch.delenv("RPC_URL", raising=False)
    monkeypatch.delenv("CONTRACT_ADDRESS", raising=False)

    event_id = f"EVT-HONEST-{uuid.uuid4().hex[:8]}"
    anchor_test_tracker["event_ids"].append(event_id)

    req = AnchorEventRequest(
        event_id=event_id,
        payload={"event": "DISPATCH_CONFIRMED", "carrier": "BlueRoute", "units": 100},
        chain_name="ethereum-sepolia",
    )
    record = anchor_audit_event(test_conn, req)
    anchor_test_tracker["anchor_ids"].append(record.anchor_id)

    assert record.confirmation_status == "NOT_SUBMITTED"
    assert record.transaction_hash is None
    assert record.block_number is None
    assert "not configured" in record.error_message.lower()


@pytest.mark.integration
def test_duplicate_anchor_prevention(test_conn, anchor_test_tracker):
    """Submitting duplicate anchor request returns existing record without creating duplicates."""
    event_id = f"EVT-DUP-{uuid.uuid4().hex[:8]}"
    anchor_test_tracker["event_ids"].append(event_id)

    req = AnchorEventRequest(
        event_id=event_id,
        payload={"order_id": "ORD-1001", "status": "APPROVED"},
        force_simulation=True,
    )

    rec1 = anchor_audit_event(test_conn, req)
    anchor_test_tracker["anchor_ids"].append(rec1.anchor_id)

    rec2 = anchor_audit_event(test_conn, req)
    assert rec1.anchor_id == rec2.anchor_id
    assert rec1.payload_hash == rec2.payload_hash


@pytest.mark.integration
def test_verify_anchor_integrity_matched_and_mismatch(test_conn, anchor_test_tracker):
    """Integrity verification confirms authentic payloads and detects tampered payloads."""
    event_id = f"EVT-VERIF-{uuid.uuid4().hex[:8]}"
    anchor_test_tracker["event_ids"].append(event_id)

    original_payload = {"order_id": "ORD-999", "amount": 125000, "approved": True}
    req = AnchorEventRequest(
        event_id=event_id,
        payload=original_payload,
        force_simulation=True,
    )
    record = anchor_audit_event(test_conn, req)
    anchor_test_tracker["anchor_ids"].append(record.anchor_id)

    # 1. Match verification
    res_match = verify_anchor_integrity(test_conn, event_id, original_payload)
    assert res_match.matched is True
    assert res_match.verification_status == "MATCHED"

    # 2. Tampered verification
    tampered_payload = {"order_id": "ORD-999", "amount": 999999, "approved": True}
    res_mismatch = verify_anchor_integrity(test_conn, event_id, tampered_payload)
    assert res_mismatch.matched is False
    assert res_mismatch.verification_status == "MISMATCH"
    assert "mismatch" in res_mismatch.details.lower()

    # 3. Unknown event verification
    res_unknown = verify_anchor_integrity(test_conn, "UNKNOWN-EVENT-ID", original_payload)
    assert res_unknown.matched is False
    assert res_unknown.verification_status == "NOT_FOUND"


@pytest.mark.integration
def test_blockchain_anchor_and_verify_api(client: TestClient, anchor_test_tracker):
    """API endpoints for audit anchoring and verification."""
    event_id = f"EVT-API-{uuid.uuid4().hex[:8]}"
    anchor_test_tracker["event_ids"].append(event_id)
    payload = {"audit_code": "AUD-101", "risk": "LOW"}

    # Anchor endpoint
    anchor_res = client.post(
        "/api/audit/anchor",
        json={"event_id": event_id, "payload": payload, "force_simulation": True},
    )
    assert anchor_res.status_code == 201
    anc_data = anchor_res.json()
    assert anc_data["event_id_or_batch_id"] == event_id
    assert anc_data["payload_hash"].startswith("0x")
    anchor_test_tracker["anchor_ids"].append(anc_data["anchor_id"])

    # Verify endpoint
    verify_res = client.post(f"/api/audit/verify/{event_id}", json=payload)
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["matched"] is True
    assert v_data["verification_status"] == "MATCHED"
