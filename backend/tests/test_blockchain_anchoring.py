"""Comprehensive Tests for Real Blockchain Audit Anchoring (Phase 7).

Verifies:
- RFC 8785 canonical JSON serialization and deterministic SHA-256 digests
- Digest invariance across key ordering, nested objects, and float serialization
- Sensitivity to modified, missing, or tampered payload elements
- Helper conversion from 0x hex string to 32 bytes
- Error sanitizer scrubbing private keys and RPC credentials
- Honest adapter status when network provider is unconfigured (zero fabricated hashes)
- Detection of chain ID mismatch and undeployed contract addresses
- Controlled Web3 adapter transaction workflow:
  * Successful broadcast and receipt confirmation (status 1 -> CONFIRMED)
  * Reverted on-chain execution (status 0 -> FAILED with receipt details)
  * Mempool timeout handling (status PENDING with persisted tx hash)
- Safe retry and duplicate anchor idempotency
- Independent on-chain state verification (via verifyAnchor or getAnchor)
- Operational status API endpoint (/api/audit/blockchain/status)
- REST API audit endpoints with genuine blockchain fields (explorer_url, confirmed_at)
- Strict test database isolation and cleanup
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.database import close_db_pool, init_db_pool
from app.main import app
from app.models.blockchain import AnchorEventRequest
from app.services.blockchain_service import (
    CanonicalHasher,
    Web3TestnetAdapter,
    anchor_audit_event,
    get_blockchain_service_status,
    sanitize_blockchain_error,
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
            cur.execute(
                "DELETE FROM event_log WHERE event_id::text = ANY(%s);",
                (tracker["event_ids"],),
            )
        test_conn.commit()
    except Exception:
        test_conn.rollback()


# ── CanonicalHasher Unit Tests ──────────────────────────────────────────────

def test_canonical_hasher_invariance():
    """CanonicalHasher produces identical digest regardless of dictionary key ordering."""
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


def test_canonical_hasher_nested_and_floats():
    """Nested dictionaries and floats serialize deterministically per RFC 8785."""
    payload1 = {
        "order": {"id": "ORD-1", "items": [{"sku": "SKU-A", "qty": 10}]},
        "rate": 12.5,
    }
    payload2 = {
        "rate": 12.5,
        "order": {"items": [{"qty": 10, "sku": "SKU-A"}], "id": "ORD-1"},
    }
    assert CanonicalHasher.compute_digest(payload1) == CanonicalHasher.compute_digest(payload2)


def test_digest_to_bytes32():
    """Hex digest strings are converted to exactly 32 bytes."""
    hex_digest = "0x" + "a" * 64
    b = CanonicalHasher.digest_to_bytes32(hex_digest)
    assert len(b) == 32
    assert isinstance(b, bytes)
    assert b == bytes.fromhex("a" * 64)

    # Without 0x prefix
    b_noprefix = CanonicalHasher.digest_to_bytes32("b" * 64)
    assert b_noprefix == bytes.fromhex("b" * 64)

    # With uppercase 0X prefix
    b_upper = CanonicalHasher.digest_to_bytes32("0X" + "c" * 64)
    assert b_upper == bytes.fromhex("c" * 64)

    # Too short
    with pytest.raises(ValueError, match="Expected 32-byte"):
        CanonicalHasher.digest_to_bytes32("0x1234")

    # Too long
    with pytest.raises(ValueError, match="Expected 32-byte"):
        CanonicalHasher.digest_to_bytes32("0x" + "a" * 66)

    # Non-hex characters
    with pytest.raises(ValueError, match="Invalid hexadecimal"):
        CanonicalHasher.digest_to_bytes32("0x" + "z" * 64)

    # Non-string input
    with pytest.raises(ValueError, match="Expected string"):
        CanonicalHasher.digest_to_bytes32(12345)  # type: ignore


def test_rfc8785_official_appendix_d_vector():
    """Verify CanonicalHasher matches official RFC 8785 Appendix D test vector byte-for-byte."""
    data = {
        "numbers": [
            333333333.33333329,
            1e30,
            4.50,
            2e-3,
            0.000000000000000000000000001,
        ],
        "string": "\u20ac$\u000f\nA'B\"\\\"/",
        "literals": [None, True, False],
    }

    # Official expected byte sequence per RFC 8785 Appendix D
    expected_bytes = (
        b'{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        b'"string":"\xe2\x82\xac$\\u000f\\nA\'B\\"\\\\\\"/"}'
    )

    actual_bytes = CanonicalHasher.canonicalize_bytes(data)
    assert actual_bytes == expected_bytes


def test_rfc8785_negative_zero_serialization():
    """RFC 8785 Section 3.2.2.3 specifies that negative zero (-0) must be serialized as 0."""
    import math
    data = {"neg_zero": math.copysign(0.0, -1.0)}
    canonical = CanonicalHasher.canonicalize(data)
    assert canonical == '{"neg_zero":0}'


# ── Secret Sanitizer Unit Tests ──────────────────────────────────────────────

def test_sanitize_blockchain_error_scrubs_secrets():
    """Sanitizer scrubs private keys, API tokens, and URLs with basic auth."""
    dummy_key = "4f3edf983ac636a65a842ce7c78d3270f293385ff7b42132a345a31b220e32aa"
    error_msg = f"Failed to sign transaction with key {dummy_key} at endpoint https://mainnet.infura.io/v3/9aa3d95b3c8440b52652308f011d6484"

    sanitized = sanitize_blockchain_error(error_msg)
    assert dummy_key not in sanitized
    assert "9aa3d95b3c8440b52652308f011d6484" not in sanitized
    assert "[REDACTED_PRIVATE_KEY]" in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


# ── Adapter Behavior Unit & Controlled Mock Tests ────────────────────────────

@pytest.mark.integration
def test_unconfigured_network_reports_honest_status(test_conn, anchor_test_tracker, monkeypatch):
    """When Web3 RPC, contract address, or private key is missing, reports NOT_SUBMITTED without fabricating hashes."""
    monkeypatch.delenv("WEB3_PROVIDER_URI", raising=False)
    monkeypatch.delenv("RPC_URL", raising=False)
    monkeypatch.delenv("CONTRACT_ADDRESS", raising=False)
    monkeypatch.delenv("BLOCKCHAIN_PRIVATE_KEY", raising=False)

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


def test_web3_adapter_chain_id_mismatch(monkeypatch):
    """Adapter detects and rejects chain ID mismatch between config and node."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111  # Sepolia

    adapter = Web3TestnetAdapter(web3_client=mock_w3)

    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://mock.rpc")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000001")
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "80002")  # Expected Polygon Amoy

    res = adapter.submit_anchor("EVT-1", "0x" + "a" * 64)
    assert res["confirmation_status"] == "FAILED"
    assert "Chain ID mismatch" in res["error_message"]
    assert res["transaction_hash"] is None


def test_web3_adapter_undeployed_contract(monkeypatch):
    """Adapter detects when target contract has no deployed bytecode."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111
    mock_w3.eth.account.from_key.return_value.address = "0x" + "2" * 40
    mock_w3.to_checksum_address = lambda x: x
    mock_w3.eth.get_code.return_value = b""  # Empty bytecode

    adapter = Web3TestnetAdapter(web3_client=mock_w3)

    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://mock.rpc")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0x" + "3" * 40)
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "11155111")

    res = adapter.submit_anchor("EVT-1", "0x" + "a" * 64)
    assert res["confirmation_status"] == "FAILED"
    assert "No smart contract deployed" in res["error_message"]


def test_web3_adapter_unauthorized_signer(monkeypatch):
    """Adapter detects when signer account is not the contract owner before broadcasting."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111

    mock_account = MagicMock()
    mock_account.address = "0xSignerAddress11111111111111111111111111"
    mock_w3.eth.account.from_key.return_value = mock_account
    mock_w3.to_checksum_address = lambda x: x
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"

    mock_contract = MagicMock()
    # Contract owner is a different address
    mock_contract.functions.owner.return_value.call.return_value = "0xDifferentOwnerAddress222222222222222222"
    mock_w3.eth.contract.return_value = mock_contract

    adapter = Web3TestnetAdapter(web3_client=mock_w3)

    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://mock.rpc")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0x" + "3" * 40)
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "11155111")

    res = adapter.submit_anchor("EVT-UNAUTH", "0x" + "a" * 64)
    assert res["confirmation_status"] == "FAILED"
    assert "is not authorized" in res["error_message"]
    assert res["transaction_hash"] is None


def test_web3_adapter_rejects_empty_event_id(monkeypatch):
    """Adapter rejects empty or whitespace event ID before broadcasting."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111
    mock_account = MagicMock()
    mock_account.address = "0xSignerAddress"
    mock_w3.eth.account.from_key.return_value = mock_account
    mock_w3.to_checksum_address = lambda x: x
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"

    adapter = Web3TestnetAdapter(web3_client=mock_w3)
    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://mock.rpc")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0x" + "3" * 40)
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "11155111")

    res = adapter.submit_anchor("   ", "0x" + "a" * 64)
    assert res["confirmation_status"] == "FAILED"
    assert "non-empty event ID" in res["error_message"]
    assert res["transaction_hash"] is None


def test_web3_adapter_rejects_zero_digest(monkeypatch):
    """Adapter rejects all-zero digest (0x00...00) before broadcasting."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111
    mock_account = MagicMock()
    mock_account.address = "0xSignerAddress"
    mock_w3.eth.account.from_key.return_value = mock_account
    mock_w3.to_checksum_address = lambda x: x
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"

    adapter = Web3TestnetAdapter(web3_client=mock_w3)
    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://mock.rpc")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0x" + "3" * 40)
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "11155111")

    res = adapter.submit_anchor("EVT-ZERO", "0x" + "00" * 32)
    assert res["confirmation_status"] == "FAILED"
    assert "Zero digest" in res["error_message"]
    assert res["transaction_hash"] is None


def test_web3_adapter_successful_mining(monkeypatch):
    """Controlled mock Web3 adapter verifies complete signing, broadcasting, and confirmed receipt."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111

    mock_account = MagicMock()
    mock_account.address = "0xSender1111111111111111111111111111111111"
    signed_obj = MagicMock()
    signed_obj.raw_transaction = b"fake-signed-raw-tx"
    mock_account.sign_transaction.return_value = signed_obj

    mock_w3.eth.account.from_key.return_value = mock_account
    mock_w3.to_checksum_address = lambda x: x
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"  # Valid contract code
    mock_w3.eth.get_transaction_count.return_value = 5
    mock_w3.eth.estimate_gas.return_value = 80000

    dummy_tx_hash = "0x" + "f" * 64
    mock_w3.eth.send_raw_transaction.return_value = bytes.fromhex("f" * 64)

    mock_contract = MagicMock()
    mock_contract.functions.recordAnchor.return_value.build_transaction.return_value = {
        "to": "0xContract",
        "data": "0x1234",
    }
    mock_w3.eth.contract.return_value = mock_contract

    # Receipt confirmation with status == 1
    mock_w3.eth.wait_for_transaction_receipt.return_value = {
        "status": 1,
        "blockNumber": 5432100,
        "gasUsed": 72500,
    }

    adapter = Web3TestnetAdapter(web3_client=mock_w3)

    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://sepolia.mock")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0xContract111111111111111111111111111111111")
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "11155111")
    monkeypatch.setenv("EXPLORER_TX_URL_PREFIX", "https://sepolia.etherscan.io/tx/")

    res = adapter.submit_anchor("EVT-CONFIRMED-1", "0x" + "a" * 64)

    assert res["confirmation_status"] == "CONFIRMED"
    assert res["receipt_status"] == 1
    assert res["block_number"] == 5432100
    assert res["gas_used"] == 72500
    assert res["transaction_hash"] == dummy_tx_hash
    assert res["explorer_url"] == f"https://sepolia.etherscan.io/tx/{dummy_tx_hash}"
    assert res["confirmed_at"] is not None


def test_web3_adapter_reverted_transaction(monkeypatch):
    """Adapter detects when an on-chain transaction reverts (receipt.status == 0) and marks FAILED."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111

    mock_account = MagicMock()
    mock_account.address = "0xSender1111111111111111111111111111111111"
    signed_obj = MagicMock()
    signed_obj.raw_transaction = b"fake-signed-raw-tx"
    mock_account.sign_transaction.return_value = signed_obj

    mock_w3.eth.account.from_key.return_value = mock_account
    mock_w3.to_checksum_address = lambda x: x
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"
    mock_w3.eth.get_transaction_count.return_value = 5
    mock_w3.eth.estimate_gas.return_value = 80000
    mock_w3.eth.send_raw_transaction.return_value = bytes.fromhex("e" * 64)

    mock_contract = MagicMock()
    mock_contract.functions.recordAnchor.return_value.build_transaction.return_value = {"to": "0xContract"}
    mock_w3.eth.contract.return_value = mock_contract

    # Receipt with status == 0 (reverted)
    mock_w3.eth.wait_for_transaction_receipt.return_value = {
        "status": 0,
        "blockNumber": 5432101,
        "gasUsed": 80000,
    }

    adapter = Web3TestnetAdapter(web3_client=mock_w3)

    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://sepolia.mock")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0xContract111111111111111111111111111111111")
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "11155111")

    res = adapter.submit_anchor("EVT-REVERT-1", "0x" + "a" * 64)

    assert res["confirmation_status"] == "FAILED"
    assert res["receipt_status"] == 0
    assert res["block_number"] == 5432101
    assert "reverted" in res["error_message"].lower()


def test_web3_adapter_mempool_timeout_pending(monkeypatch):
    """When receipt polling times out, transaction is marked PENDING without false failure."""
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.chain_id = 11155111

    mock_account = MagicMock()
    mock_account.address = "0xSender1111111111111111111111111111111111"
    signed_obj = MagicMock()
    signed_obj.raw_transaction = b"fake-signed-raw-tx"
    mock_account.sign_transaction.return_value = signed_obj

    mock_w3.eth.account.from_key.return_value = mock_account
    mock_w3.to_checksum_address = lambda x: x
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"
    mock_w3.eth.get_transaction_count.return_value = 5
    mock_w3.eth.estimate_gas.return_value = 80000

    dummy_tx_hash = "0x" + "d" * 64
    mock_w3.eth.send_raw_transaction.return_value = bytes.fromhex("d" * 64)

    mock_contract = MagicMock()
    mock_contract.functions.recordAnchor.return_value.build_transaction.return_value = {"to": "0xContract"}
    mock_w3.eth.contract.return_value = mock_contract

    # wait_for_transaction_receipt raises timeout
    mock_w3.eth.wait_for_transaction_receipt.side_effect = TimeoutError("Polling timed out after 30s")

    adapter = Web3TestnetAdapter(web3_client=mock_w3)

    monkeypatch.setenv("WEB3_PROVIDER_URI", "https://sepolia.mock")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0xContract111111111111111111111111111111111")
    monkeypatch.setenv("BLOCKCHAIN_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("CHAIN_ID", "11155111")

    res = adapter.submit_anchor("EVT-PENDING-1", "0x" + "a" * 64)

    assert res["confirmation_status"] == "PENDING"
    assert res["transaction_hash"] == dummy_tx_hash
    assert res["block_number"] is None
    assert "mempool" in res["error_message"].lower()


# ── Idempotency, Verification, and Status API Tests ─────────────────────────

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
def test_blockchain_status_service_and_api(client: TestClient, test_conn):
    """Verify /api/audit/blockchain/status provides truthful operational mode without leaking secrets."""
    res = client.get("/api/audit/blockchain/status")
    assert res.status_code == 200
    data = res.json()

    assert "mode" in data
    assert "network_name" in data
    assert "rpc_configured" in data
    assert "signer_configured" in data
    assert "total_anchors_tracked" in data
    # Ensure no secrets leaked in response
    assert "private_key" not in str(data).lower()
    assert "signer_key" not in str(data).lower()


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


@pytest.mark.integration
def test_audit_event_response_contains_blockchain_fields(client: TestClient, test_conn, anchor_test_tracker):
    """GET /api/audit/ and GET /api/audit/{id} serialize blockchain metadata fields properly."""
    event_id = str(uuid.uuid4())
    anchor_test_tracker["event_ids"].append(event_id)

    # Insert event into event_log
    with test_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO event_log (event_id, event_type, entity_type, entity_id, actor_type, actor_id, status, payload_hash)
            VALUES (%s, 'ORDER_DISPATCHED', 'ORDER', 'ORD-1001', 'OPERATOR', 'OPERATOR', 'COMPLETED', '0xHash123')
            """,
            (event_id,),
        )
        # Insert corresponding anchor with new migration 005 columns
        cur.execute(
            """
            INSERT INTO blockchain_anchors (
                event_id_or_batch_id, chain_name, chain_id, contract_address, payload_hash,
                transaction_hash, block_number, confirmation_status, receipt_status,
                explorer_url, anchored_at, confirmed_at
            ) VALUES (
                %s, 'ethereum-sepolia', 11155111, '0xContractAddr', '0xHash123',
                '0xTxHash456', 998877, 'CONFIRMED', 1,
                'https://sepolia.etherscan.io/tx/0xTxHash456', NOW(), NOW()
            ) RETURNING anchor_id;
            """,
            (event_id,),
        )
        anc_id = cur.fetchone()[0]
        anchor_test_tracker["anchor_ids"].append(str(anc_id))
        test_conn.commit()

    # Query single event endpoint
    res = client.get(f"/api/audit/{event_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["event_id"] == event_id
    assert detail["blockchain_status"] == "CONFIRMED"
    assert detail["tx_hash"] == "0xTxHash456"
    assert detail["block_number"] == 998877
    assert detail["explorer_url"] == "https://sepolia.etherscan.io/tx/0xTxHash456"
    assert detail["receipt_status"] == 1
    assert detail["confirmed_at"] is not None

    # Verify GET /api/audit/anchors lists this anchor
    res_anchors = client.get(f"/api/audit/anchors?event_id={event_id}")
    assert res_anchors.status_code == 200
    anchors_list = res_anchors.json()
    assert len(anchors_list) >= 1
    assert anchors_list[0]["event_id_or_batch_id"] == event_id
    assert anchors_list[0]["transaction_hash"] == "0xTxHash456"

    # Verify empty-payload verify does not falsify mismatch
    res_verif = client.post(f"/api/audit/verify/{event_id}", json={})
    assert res_verif.status_code == 200
    verif_data = res_verif.json()
    assert verif_data["digest_verified"] is True
    assert verif_data["verification_status"] == "MATCHED"

    # Verify on-chain verification endpoint works
    res_on_chain = client.post(f"/api/audit/verify-on-chain/{event_id}")
    assert res_on_chain.status_code == 200
    on_chain_data = res_on_chain.json()
    assert "verification_status" in on_chain_data
    assert on_chain_data["digest_verified"] is True
