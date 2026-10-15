"""Tests for Phase 9 Audit Chain, Immutability & Merkle Trees."""

import hashlib
import json
import pytest
from app.services.audit_chain import (
    GENESIS_HASH,
    MerkleTree,
    append_chained_event,
    compute_entry_hash,
    create_batch_merkle_checkpoint,
    verify_chain,
)
from app.services.blockchain_service import CanonicalHasher


def test_rfc8785_canonicalization_test_vectors():
    """Verify deterministic canonical serialization against RFC 8785 test vectors."""
    # 1. Key ordering (must sort alphabetically)
    obj1 = {"z": 1, "a": 2, "m": 3}
    expected1 = '{"a":2,"m":3,"z":1}'
    assert CanonicalHasher.canonicalize(obj1) == expected1

    # 2. Number formatting (no exponential for small numbers, no trailing zeros)
    obj2 = {"val": 100.5, "zero": 0, "neg": -42}
    expected2 = '{"neg":-42,"val":100.5,"zero":0}'
    assert CanonicalHasher.canonicalize(obj2) == expected2

    # 3. Unicode and special characters
    obj3 = {"city": "मुंबई", "symbol": "₹", "desc": "HR Coil steel"}
    canon3 = CanonicalHasher.canonicalize(obj3)
    assert "मुंबई" in canon3
    assert "₹" in canon3
    # Digest should be stable and 0x-prefixed 64 hex chars
    digest3 = CanonicalHasher.compute_digest(obj3)
    assert digest3.startswith("0x") and len(digest3) == 66


def test_merkle_tree_construction_and_proof_verification():
    """Build Merkle Tree from leaf hashes and verify cryptographic proof paths."""
    leaves = [
        f"0x{hashlib.sha256(f'event-{i}'.encode()).hexdigest()}"
        for i in range(8)
    ]
    tree = MerkleTree(leaves)
    assert tree.root.startswith("0x") and len(tree.root) == 66

    # Verify proofs for each leaf
    for i, leaf in enumerate(leaves):
        proof = tree.get_proof(i)
        assert len(proof) == 3  # log2(8) = 3 layers
        is_valid = MerkleTree.verify_proof(leaf, proof, tree.root)
        assert is_valid is True

    # Tampered leaf fails verification
    tampered_leaf = "0x" + "f" * 64
    proof_0 = tree.get_proof(0)
    assert MerkleTree.verify_proof(tampered_leaf, proof_0, tree.root) is False


@pytest.mark.integration
def test_append_chained_events_and_verify(test_conn):
    """Append a series of chained events and verify the complete hash chain."""
    ev1 = None
    ev2 = None
    ev3 = None
    checkpoint = None
    try:
        ev1 = append_chained_event(
            test_conn,
            event_type="DISPATCH_ORDER",
            entity_type="ORDER",
            entity_id="ORD-CHAIN-01",
            payload={"order_id": "ORD-CHAIN-01", "qty": 100.0},
        )
        ev2 = append_chained_event(
            test_conn,
            event_type="SHIPMENT_DEPARTED",
            entity_type="SHIPMENT",
            entity_id="SHP-CHAIN-01",
            payload={"shipment_id": "SHP-CHAIN-01", "carrier": "CONCOR"},
        )
        ev3 = append_chained_event(
            test_conn,
            event_type="SHIPMENT_DELIVERED",
            entity_type="SHIPMENT",
            entity_id="SHP-CHAIN-01",
            payload={"shipment_id": "SHP-CHAIN-01", "delivered": True},
        )

        assert ev2["prev_hash"] == ev1["entry_hash"]
        assert ev3["prev_hash"] == ev2["entry_hash"]

        # Verify chain from ev1's sequence number
        res = verify_chain(test_conn, from_seq=ev1["sequence_num"], limit=10)
        assert res["verified"] is True
        assert res["checked_events"] >= 3
        assert res["first_broken_sequence"] is None

        # Create Merkle batch checkpoint
        checkpoint = create_batch_merkle_checkpoint(
            test_conn,
            start_seq=ev1["sequence_num"],
            end_seq=ev3["sequence_num"],
        )
        assert checkpoint["merkle_root"].startswith("0x")
        assert checkpoint["leaf_count"] >= 3
        assert checkpoint["confirmation_status"] == "CONFIRMED"
    finally:
        with test_conn.cursor() as cur:
            if checkpoint and "anchor_id" in checkpoint:
                cur.execute("DELETE FROM blockchain_anchors WHERE anchor_id = %s;", (checkpoint["anchor_id"],))
            ev_ids = [ev["event_id"] for ev in [ev1, ev2, ev3] if ev and "event_id" in ev]
            if ev_ids:
                cur.execute("DELETE FROM event_log WHERE event_id::text = ANY(%s);", (ev_ids,))
            test_conn.commit()
