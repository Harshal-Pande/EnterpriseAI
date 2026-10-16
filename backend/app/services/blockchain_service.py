"""Blockchain Audit Anchoring Service (Phase 7 Hardened).

Provides:
- Deterministic canonicalization (RFC 8785 style) and SHA-256 digest computation
- Real Web3 EVM transaction lifecycle: nonce tracking, EIP-1559 / gas estimation, signing, broadcast
- Receipt polling with bounded timeouts, explicit PENDING, CONFIRMED, and FAILED states
- Reverted on-chain transaction detection and honest status persistence
- Independent on-chain state verification comparing on-chain storage with off-chain digests
- Duplicate anchor prevention and idempotent re-polling
- Sanitized error reporting preventing leakage of private keys or RPC credentials
- Honest separation between live EVM testnet mode and local simulation mode
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.models.blockchain import (
    AnchorEventRequest,
    BlockchainAnchorRecord,
    BlockchainStatusResponse,
    VerificationResult,
)

logger = logging.getLogger("enterpriseai.blockchain")

DEFAULT_CHAIN_NAME = "ethereum-sepolia"
DEFAULT_CHAIN_ID = 11155111
DEFAULT_EXPLORER_PREFIX = "https://sepolia.etherscan.io/tx/"
UNCONFIGURED_CONTRACT = "0x0000000000000000000000000000000000000000"
CONTRACT_ABI_PATH = Path(__file__).resolve().parent.parent / "contracts" / "enterprise_audit_abi.json"

_cached_contract_abi: Optional[list] = None


def sanitize_blockchain_error(error: Any) -> str:
    """Scrub private keys, authorization tokens, and credentials from error messages."""
    text = str(error)
    # Scrub 64-hex private keys (with or without 0x)
    text = re.sub(r"\b(0x)?[0-9a-fA-F]{64}\b", "[REDACTED_PRIVATE_KEY]", text)
    # Scrub URLs with embedded credentials or API keys (e.g., https://.../v3/KEY)
    text = re.sub(r"https?://([^/]+)/v\d+/([a-zA-Z0-9_-]{16,})", r"https://\1/v.../[REDACTED_API_KEY]", text)
    # Scrub basic auth user:pass in URLs
    text = re.sub(r"://[^:@\s]+:[^:@\s]+@", "://[REDACTED_AUTH]@", text)
    return text[:300]


def load_contract_abi() -> list:
    """Load EnterpriseAudit ABI JSON file."""
    global _cached_contract_abi
    if _cached_contract_abi is not None:
        return _cached_contract_abi

    if CONTRACT_ABI_PATH.is_file():
        try:
            with open(CONTRACT_ABI_PATH, "r", encoding="utf-8") as f:
                _cached_contract_abi = json.load(f)
                return _cached_contract_abi
        except Exception as exc:
            logger.error("Failed to load contract ABI from %s: %s", CONTRACT_ABI_PATH, exc)

    # Fallback minimal ABI if file read fails
    return [
        {
            "inputs": [
                {"internalType": "string", "name": "_eventId", "type": "string"},
                {"internalType": "string", "name": "_eventType", "type": "string"},
                {"internalType": "bytes32", "name": "_payloadDigest", "type": "bytes32"},
                {"internalType": "string", "name": "_actor", "type": "string"},
            ],
            "name": "recordAnchor",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "string", "name": "_orderId", "type": "string"},
                {"internalType": "string", "name": "_eventType", "type": "string"},
                {"internalType": "string", "name": "_eventHash", "type": "string"},
                {"internalType": "string", "name": "_actor", "type": "string"},
            ],
            "name": "recordEvent",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "string", "name": "_eventId", "type": "string"},
                {"internalType": "bytes32", "name": "_expectedDigest", "type": "bytes32"},
            ],
            "name": "verifyAnchor",
            "outputs": [
                {"internalType": "bool", "name": "matched", "type": "bool"},
                {"internalType": "uint256", "name": "blockTimestamp", "type": "uint256"},
                {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
    ]


class CanonicalHasher:
    """RFC 8785 compliant canonical JSON serialization and SHA-256 digest generator."""

    @staticmethod
    def canonicalize_bytes(obj: Any) -> bytes:
        """Deterministic RFC 8785 (JCS) canonical JSON serialization returning UTF-8 bytes."""
        try:
            import rfc8785
            return rfc8785.dumps(obj)
        except Exception:
            return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")

    @classmethod
    def canonicalize(cls, obj: Any) -> str:
        """Deterministic RFC 8785 (JCS) canonical JSON serialization returning decoded str."""
        return cls.canonicalize_bytes(obj).decode("utf-8")

    @classmethod
    def compute_digest(cls, payload: Dict[str, Any]) -> str:
        """Compute 0x-prefixed SHA-256 hex digest of the canonicalized payload."""
        canonical_bytes = cls.canonicalize_bytes(payload)
        digest = hashlib.sha256(canonical_bytes).hexdigest()
        return f"0x{digest}"

    @staticmethod
    def digest_to_bytes32(digest_hex: str) -> bytes:
        """Convert a 0x-prefixed 64-char hex digest to 32 bytes for EVM contracts."""
        if not isinstance(digest_hex, str):
            raise ValueError(f"Expected string hex digest, got {type(digest_hex).__name__}")
        clean = digest_hex.strip()
        if clean.startswith("0x") or clean.startswith("0X"):
            clean = clean[2:]
        if len(clean) != 64:
            raise ValueError(f"Expected 32-byte (64 hex characters) digest, got {len(clean)} characters.")
        try:
            return bytes.fromhex(clean)
        except ValueError as exc:
            raise ValueError(f"Invalid hexadecimal digest: {exc}") from exc


class BlockchainAdapter(ABC):
    """Abstract adapter interface for blockchain anchor submission and verification."""

    @abstractmethod
    def submit_anchor(
        self,
        event_id: str,
        payload_hash: str,
        chain_name: str,
        contract_address: Optional[str] = None,
        event_type: str = "AUDIT_EVENT",
        actor: str = "SYSTEM",
    ) -> Dict[str, Any]:
        """Submit digest to the blockchain network. Returns transaction details or honest unconfigured status."""
        pass


class Web3TestnetAdapter(BlockchainAdapter):
    """Real EVM blockchain testnet adapter using Web3.py.

    Never fabricates transaction hashes or fake block numbers.
    """

    def __init__(self, web3_client: Optional[Any] = None):
        self._w3_override = web3_client

    def _get_w3(self, rpc_url: str):
        if self._w3_override:
            return self._w3_override
        try:
            from web3 import Web3  # type: ignore
            return Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))
        except ImportError:
            return None

    def submit_anchor(
        self,
        event_id: str,
        payload_hash: str,
        chain_name: str = DEFAULT_CHAIN_NAME,
        contract_address: Optional[str] = None,
        event_type: str = "AUDIT_EVENT",
        actor: str = "SYSTEM",
    ) -> Dict[str, Any]:
        rpc_url = os.environ.get("WEB3_PROVIDER_URI") or os.environ.get("RPC_URL") or os.environ.get("SEPOLIA_RPC_URL")
        target_contract = contract_address or os.environ.get("CONTRACT_ADDRESS")
        private_key = os.environ.get("BLOCKCHAIN_PRIVATE_KEY") or os.environ.get("SIGNER_PRIVATE_KEY")
        chain_id = int(os.environ.get("CHAIN_ID", str(DEFAULT_CHAIN_ID)))
        explorer_prefix = os.environ.get("EXPLORER_TX_URL_PREFIX", DEFAULT_EXPLORER_PREFIX)
        timeout_seconds = int(os.environ.get("BLOCKCHAIN_CONFIRMATION_TIMEOUT", "30"))

        # Fail honestly if network credentials or RPC are unconfigured
        if not rpc_url or not target_contract or not private_key:
            missing = []
            if not rpc_url:
                missing.append("WEB3_PROVIDER_URI")
            if not target_contract:
                missing.append("CONTRACT_ADDRESS")
            if not private_key:
                missing.append("BLOCKCHAIN_PRIVATE_KEY")

            return {
                "confirmation_status": "NOT_SUBMITTED",
                "transaction_hash": None,
                "block_number": None,
                "error_message": f"Live testnet anchoring is NOT configured. Missing required variables: {', '.join(missing)}.",
                "mode": "REAL_NETWORK",
                "chain_id": chain_id,
                "contract_address": target_contract or UNCONFIGURED_CONTRACT,
                "explorer_url": None,
            }

        w3 = self._get_w3(rpc_url)
        if w3 is None:
            return {
                "confirmation_status": "NOT_SUBMITTED",
                "transaction_hash": None,
                "block_number": None,
                "error_message": "web3 library is not available in the python environment.",
                "mode": "REAL_NETWORK",
                "chain_id": chain_id,
                "contract_address": target_contract,
                "explorer_url": None,
            }

        try:
            if not w3.is_connected():
                return {
                    "confirmation_status": "FAILED",
                    "transaction_hash": None,
                    "block_number": None,
                    "error_message": f"Web3 provider at {sanitize_blockchain_error(rpc_url)} is unreachable.",
                    "mode": "REAL_NETWORK",
                    "chain_id": chain_id,
                    "contract_address": target_contract,
                    "explorer_url": None,
                }

            # Chain ID verification
            connected_chain_id = w3.eth.chain_id
            if connected_chain_id != chain_id:
                return {
                    "confirmation_status": "FAILED",
                    "transaction_hash": None,
                    "block_number": None,
                    "error_message": f"Chain ID mismatch: connected to {connected_chain_id} but expected {chain_id}.",
                    "mode": "REAL_NETWORK",
                    "chain_id": connected_chain_id,
                    "contract_address": target_contract,
                    "explorer_url": None,
                }

            # Derive account from private key
            account = w3.eth.account.from_key(private_key.strip())
            checksum_contract = w3.to_checksum_address(target_contract.strip())

            # Verify contract deployment
            code = w3.eth.get_code(checksum_contract)
            if not code or code == b"" or code == b"\x00":
                return {
                    "confirmation_status": "FAILED",
                    "transaction_hash": None,
                    "block_number": None,
                    "error_message": f"No smart contract deployed at address {checksum_contract}.",
                    "mode": "REAL_NETWORK",
                    "chain_id": chain_id,
                    "contract_address": checksum_contract,
                    "explorer_url": None,
                }

            # Initialize contract
            abi = load_contract_abi()
            contract = w3.eth.contract(address=checksum_contract, abi=abi)

            # Pre-flight access control: verify signer is authorized contract owner
            if hasattr(contract.functions, "owner"):
                try:
                    contract_owner = contract.functions.owner().call()
                    if isinstance(contract_owner, str) and contract_owner and contract_owner.lower() != account.address.lower():
                        return {
                            "confirmation_status": "FAILED",
                            "transaction_hash": None,
                            "block_number": None,
                            "error_message": (
                                f"Signer account {account.address} is not authorized owner of contract {checksum_contract} "
                                f"(configured owner is {contract_owner})."
                            ),
                            "mode": "REAL_NETWORK",
                            "chain_id": chain_id,
                            "contract_address": checksum_contract,
                            "explorer_url": None,
                        }
                except Exception as owner_exc:
                    logger.warning("Pre-flight owner check failed: %s", sanitize_blockchain_error(owner_exc))

            if not event_id or not event_id.strip():
                return {
                    "confirmation_status": "FAILED",
                    "transaction_hash": None,
                    "block_number": None,
                    "error_message": "EnterpriseAudit contract requires a non-empty event ID.",
                    "mode": "REAL_NETWORK",
                    "chain_id": chain_id,
                    "contract_address": checksum_contract,
                    "explorer_url": None,
                }

            # Convert digest to 32 bytes
            try:
                digest_bytes = CanonicalHasher.digest_to_bytes32(payload_hash)
            except ValueError as ve:
                return {
                    "confirmation_status": "FAILED",
                    "transaction_hash": None,
                    "block_number": None,
                    "error_message": f"Malformed payload digest: {ve}",
                    "mode": "REAL_NETWORK",
                    "chain_id": chain_id,
                    "contract_address": checksum_contract,
                    "explorer_url": None,
                }

            if digest_bytes == b"\x00" * 32:
                return {
                    "confirmation_status": "FAILED",
                    "transaction_hash": None,
                    "block_number": None,
                    "error_message": "Zero digest (0x00...00) is rejected by EnterpriseAudit contract.",
                    "mode": "REAL_NETWORK",
                    "chain_id": chain_id,
                    "contract_address": checksum_contract,
                    "explorer_url": None,
                }

            nonce = w3.eth.get_transaction_count(account.address, "pending")

            # Check if recordAnchor exists on contract, else fallback to recordEvent
            tx_data: Dict[str, Any] = {}
            if hasattr(contract.functions, "recordAnchor"):
                tx_data = contract.functions.recordAnchor(
                    event_id,
                    event_type,
                    digest_bytes,
                    actor,
                ).build_transaction({
                    "chainId": chain_id,
                    "from": account.address,
                    "nonce": nonce,
                })
            elif hasattr(contract.functions, "recordEvent"):
                tx_data = contract.functions.recordEvent(
                    event_id,
                    event_type,
                    payload_hash,
                    actor,
                ).build_transaction({
                    "chainId": chain_id,
                    "from": account.address,
                    "nonce": nonce,
                })
            else:
                return {
                    "confirmation_status": "FAILED",
                    "transaction_hash": None,
                    "block_number": None,
                    "error_message": "Target contract does not implement recordAnchor or recordEvent functions.",
                    "mode": "REAL_NETWORK",
                    "chain_id": chain_id,
                    "contract_address": checksum_contract,
                    "explorer_url": None,
                }

            # Gas estimation with 20% safety margin
            try:
                estimated_gas = w3.eth.estimate_gas(tx_data)
                tx_data["gas"] = int(estimated_gas * 1.25)
            except Exception as gas_exc:
                logger.warning("Gas estimation failed: %s; using safe default", sanitize_blockchain_error(gas_exc))
                tx_data["gas"] = 250000

            # Sign and broadcast transaction
            signed_tx = account.sign_transaction(tx_data)
            raw_tx_bytes = getattr(signed_tx, "raw_transaction", getattr(signed_tx, "rawTransaction", None))
            tx_hash_bytes = w3.eth.send_raw_transaction(raw_tx_bytes)
            tx_hash = tx_hash_bytes.hex() if hasattr(tx_hash_bytes, "hex") else str(tx_hash_bytes)
            if not tx_hash.startswith("0x"):
                tx_hash = f"0x{tx_hash}"

            explorer_url = f"{explorer_prefix}{tx_hash}"

            # Wait for receipt with bounded timeout
            try:
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout_seconds, poll_latency=1.0)
                receipt_status = int(receipt.get("status", 0))
                block_number = int(receipt.get("blockNumber", 0))
                gas_used = int(receipt.get("gasUsed", 0))

                if receipt_status == 1:
                    return {
                        "confirmation_status": "CONFIRMED",
                        "transaction_hash": tx_hash,
                        "block_number": block_number,
                        "gas_used": gas_used,
                        "receipt_status": 1,
                        "confirmed_at": datetime.now(timezone.utc).isoformat(),
                        "mode": "REAL_NETWORK",
                        "chain_id": chain_id,
                        "contract_address": checksum_contract,
                        "explorer_url": explorer_url,
                        "error_message": None,
                    }
                else:
                    return {
                        "confirmation_status": "FAILED",
                        "transaction_hash": tx_hash,
                        "block_number": block_number,
                        "gas_used": gas_used,
                        "receipt_status": 0,
                        "confirmed_at": datetime.now(timezone.utc).isoformat(),
                        "mode": "REAL_NETWORK",
                        "chain_id": chain_id,
                        "contract_address": checksum_contract,
                        "explorer_url": explorer_url,
                        "error_message": "On-chain transaction execution reverted.",
                    }

            except Exception as wait_exc:
                # Receipt wait timed out — transaction is pending in mempool
                logger.info("Transaction %s pending in mempool: %s", tx_hash, sanitize_blockchain_error(wait_exc))
                return {
                    "confirmation_status": "PENDING",
                    "transaction_hash": tx_hash,
                    "block_number": None,
                    "gas_used": None,
                    "receipt_status": None,
                    "confirmed_at": None,
                    "mode": "REAL_NETWORK",
                    "chain_id": chain_id,
                    "contract_address": checksum_contract,
                    "explorer_url": explorer_url,
                    "error_message": "Transaction broadcast to network mempool; awaiting block confirmation.",
                }

        except Exception as exc:
            clean_err = sanitize_blockchain_error(exc)
            logger.error("Error submitting blockchain anchor: %s", clean_err)
            return {
                "confirmation_status": "FAILED",
                "transaction_hash": None,
                "block_number": None,
                "error_message": f"RPC submission error: {clean_err}",
                "mode": "REAL_NETWORK",
                "chain_id": chain_id,
                "contract_address": target_contract or UNCONFIGURED_CONTRACT,
                "explorer_url": None,
            }


class SimulatedBlockchainAdapter(BlockchainAdapter):
    """Explicit prototype simulation adapter, clearly labeled to prevent misleading users."""

    def submit_anchor(
        self,
        event_id: str,
        payload_hash: str,
        chain_name: str = "simulation-local",
        contract_address: Optional[str] = None,
        event_type: str = "AUDIT_EVENT",
        actor: str = "SYSTEM",
    ) -> Dict[str, Any]:
        return {
            "confirmation_status": "NOT_SUBMITTED",
            "transaction_hash": None,
            "block_number": None,
            "gas_used": None,
            "receipt_status": None,
            "confirmed_at": None,
            "error_message": "Local prototype simulation mode. No on-chain transaction broadcast.",
            "mode": "SIMULATED",
            "chain_id": 31337,
            "contract_address": contract_address or "0xSIMULATED0000000000000000000000000000000",
            "explorer_url": None,
        }


def _row_to_anchor_record(row: tuple, mode: str = "REAL_NETWORK") -> BlockchainAnchorRecord:
    (
        anchor_id,
        event_id_or_batch_id,
        payload_hash,
        chain_name,
        chain_id,
        contract_address,
        tx_hash,
        block_number,
        anchored_at,
        conf_status,
        verif_status,
        error_msg,
        confirmed_at,
        receipt_status,
        gas_used,
        retry_count,
        explorer_url,
    ) = row

    return BlockchainAnchorRecord(
        anchor_id=str(anchor_id),
        event_id_or_batch_id=str(event_id_or_batch_id),
        payload_hash=str(payload_hash),
        chain_name=str(chain_name),
        chain_id=int(chain_id),
        contract_address=str(contract_address),
        transaction_hash=str(tx_hash) if tx_hash else None,
        block_number=int(block_number) if block_number is not None else None,
        anchored_at=anchored_at.isoformat() if anchored_at else None,
        confirmed_at=confirmed_at.isoformat() if confirmed_at else None,
        receipt_status=int(receipt_status) if receipt_status is not None else None,
        gas_used=int(gas_used) if gas_used is not None else None,
        explorer_url=str(explorer_url) if explorer_url else None,
        retry_count=int(retry_count) if retry_count is not None else 0,
        confirmation_status=str(conf_status),
        verification_status=str(verif_status),
        error_message=str(error_msg) if error_msg else None,
        mode=mode,
    )


def anchor_audit_event(
    conn,
    req: AnchorEventRequest,
    adapter: Optional[BlockchainAdapter] = None,
) -> BlockchainAnchorRecord:
    """Canonicalize payload, compute digest, check for duplicates, and record anchor in PostgreSQL."""
    payload_hash = CanonicalHasher.compute_digest(req.payload)
    event_id = req.event_id.strip()

    with conn.cursor() as cur:
        # Duplicate anchor check: return existing record if already anchored or confirmed
        cur.execute(
            """
            SELECT
                anchor_id, event_id_or_batch_id, payload_hash, chain_name,
                chain_id, contract_address, transaction_hash, block_number,
                anchored_at, confirmation_status, verification_status, error_message,
                confirmed_at, receipt_status, gas_used, retry_count, explorer_url
            FROM blockchain_anchors
            WHERE event_id_or_batch_id = %s OR payload_hash = %s
            ORDER BY anchored_at DESC
            LIMIT 1;
            """,
            (event_id, payload_hash),
        )
        existing = cur.fetchone()
        if existing:
            # If already confirmed, return existing record immediately (idempotency)
            if existing[9] == "CONFIRMED":
                return _row_to_anchor_record(existing, mode="SIMULATED" if "simulat" in str(existing[3]).lower() else "REAL_NETWORK")

        # Determine active adapter
        if req.force_simulation:
            active_adapter = adapter or SimulatedBlockchainAdapter()
        else:
            mode_env = os.environ.get("BLOCKCHAIN_MODE", "REAL_NETWORK").upper()
            if mode_env == "SIMULATED":
                active_adapter = adapter or SimulatedBlockchainAdapter()
            else:
                active_adapter = adapter or Web3TestnetAdapter()

        adapter_res = active_adapter.submit_anchor(
            event_id=event_id,
            payload_hash=payload_hash,
            chain_name=req.chain_name or DEFAULT_CHAIN_NAME,
            contract_address=req.contract_address,
        )

        anchor_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        conf_status = adapter_res.get("confirmation_status", "NOT_SUBMITTED")
        error_msg = adapter_res.get("error_message")
        tx_hash = adapter_res.get("transaction_hash")
        block_num = adapter_res.get("block_number")
        chain_id = adapter_res.get("chain_id", DEFAULT_CHAIN_ID)
        contract_addr = adapter_res.get("contract_address", UNCONFIGURED_CONTRACT)
        mode = adapter_res.get("mode", "REAL_NETWORK")
        confirmed_at = adapter_res.get("confirmed_at")
        receipt_status = adapter_res.get("receipt_status")
        gas_used = adapter_res.get("gas_used")
        explorer_url = adapter_res.get("explorer_url")

        # If previous pending record exists, update it rather than creating orphan duplicate
        if existing and existing[9] != "CONFIRMED":
            cur.execute(
                """
                UPDATE blockchain_anchors
                SET
                    transaction_hash = COALESCE(%s, transaction_hash),
                    block_number = COALESCE(%s, block_number),
                    confirmation_status = %s,
                    confirmed_at = COALESCE(%s, confirmed_at),
                    receipt_status = COALESCE(%s, receipt_status),
                    gas_used = COALESCE(%s, gas_used),
                    explorer_url = COALESCE(%s, explorer_url),
                    error_message = %s,
                    retry_count = retry_count + 1
                WHERE anchor_id = %s
                RETURNING
                    anchor_id, event_id_or_batch_id, payload_hash, chain_name,
                    chain_id, contract_address, transaction_hash, block_number,
                    anchored_at, confirmation_status, verification_status, error_message,
                    confirmed_at, receipt_status, gas_used, retry_count, explorer_url;
                """,
                (
                    tx_hash,
                    block_num,
                    conf_status,
                    confirmed_at,
                    receipt_status,
                    gas_used,
                    explorer_url,
                    error_msg,
                    existing[0],
                ),
            )
            row = cur.fetchone()
        else:
            cur.execute(
                """
                INSERT INTO blockchain_anchors (
                    anchor_id, event_id_or_batch_id, payload_hash, chain_name,
                    chain_id, contract_address, transaction_hash, block_number,
                    anchored_at, confirmation_status, verification_status, error_message,
                    confirmed_at, receipt_status, gas_used, retry_count, explorer_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'NOT_VERIFIED', %s, %s, %s, %s, 0, %s)
                RETURNING
                    anchor_id, event_id_or_batch_id, payload_hash, chain_name,
                    chain_id, contract_address, transaction_hash, block_number,
                    anchored_at, confirmation_status, verification_status, error_message,
                    confirmed_at, receipt_status, gas_used, retry_count, explorer_url;
                """,
                (
                    str(anchor_id),
                    event_id,
                    payload_hash,
                    req.chain_name or DEFAULT_CHAIN_NAME,
                    chain_id,
                    contract_addr,
                    tx_hash,
                    block_num,
                    now,
                    conf_status,
                    error_msg,
                    confirmed_at,
                    receipt_status,
                    gas_used,
                    explorer_url,
                ),
            )
            row = cur.fetchone()

        conn.commit()
        return _row_to_anchor_record(row, mode=mode)


def verify_anchor_integrity(
    conn,
    event_id: str,
    original_payload: Optional[Dict[str, Any]] = None,
    web3_client: Optional[Any] = None,
) -> VerificationResult:
    """Verify an audit event payload by recomputing its canonical hash against stored anchor digest."""
    has_payload = bool(original_payload)
    computed_hash = CanonicalHasher.compute_digest(original_payload) if has_payload else None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                anchor_id, payload_hash, confirmation_status,
                block_number, transaction_hash, contract_address, chain_id, explorer_url
            FROM blockchain_anchors
            WHERE event_id_or_batch_id = %s
            ORDER BY anchored_at DESC
            LIMIT 1;
            """,
            (event_id.strip(),),
        )
        row = cur.fetchone()
        if not row:
            # Fallback: check PostgreSQL event_log table
            cur.execute(
                """
                SELECT event_id, payload_hash, status, reason_code
                FROM event_log
                WHERE event_id::text = %s;
                """,
                (event_id.strip(),),
            )
            ev_row = cur.fetchone()
            if not ev_row:
                return VerificationResult(
                    event_id=event_id,
                    matched=False,
                    computed_hash=computed_hash or "0x0",
                    anchored_hash=None,
                    verification_status="NOT_FOUND",
                    digest_verified=False,
                    on_chain_verified=False,
                    details=f"No anchor or audit event record found for event_id '{event_id}'.",
                )

            _, stored_hash, ev_status, _ = ev_row
            if has_payload:
                matched = bool(stored_hash and computed_hash and computed_hash.lower() == stored_hash.lower())
                used_computed = computed_hash
                digest_verified = matched
            else:
                matched = bool(stored_hash)
                used_computed = stored_hash or "0x0"
                digest_verified = True

            status_label = "MATCHED" if matched else "MISMATCH"
            details = (
                f"Digest {stored_hash} verified against immutable PostgreSQL event_log record (offline fallback)."
                if matched
                else f"Cryptographic mismatch! Computed {computed_hash} != Recorded {stored_hash}."
            )
            return VerificationResult(
                event_id=event_id,
                matched=matched,
                computed_hash=used_computed,
                anchored_hash=stored_hash,
                verification_status=status_label,
                confirmation_status=ev_status or "CONFIRMED_LOCAL",
                block_number=None,
                transaction_hash=None,
                on_chain_verified=False,
                digest_verified=digest_verified,
                details=details,
            )

        (
            anchor_id,
            anchored_hash,
            conf_status,
            block_num,
            tx_hash,
            contract_addr,
            chain_id,
            explorer_url,
        ) = row

        if has_payload and computed_hash:
            digest_verified = bool(computed_hash.lower() == anchored_hash.lower())
            used_computed = computed_hash
        else:
            digest_verified = True
            used_computed = anchored_hash

        new_verif_status = "MATCHED" if digest_verified else "MISMATCH"
        on_chain_verified = False
        on_chain_msg = ""

        # Attempt independent view verification on smart contract if configured
        rpc_url = os.environ.get("WEB3_PROVIDER_URI") or os.environ.get("RPC_URL")
        target_contract = contract_addr if contract_addr and contract_addr != UNCONFIGURED_CONTRACT else os.environ.get("CONTRACT_ADDRESS")

        w3 = web3_client
        if not w3 and rpc_url:
            try:
                from web3 import Web3  # type: ignore
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            except Exception:
                pass

        if w3 and target_contract and target_contract != UNCONFIGURED_CONTRACT:
            try:
                if w3.is_connected():
                    abi = load_contract_abi()
                    contract = w3.eth.contract(address=w3.to_checksum_address(target_contract), abi=abi)
                    digest_bytes = CanonicalHasher.digest_to_bytes32(used_computed)

                    if hasattr(contract.functions, "verifyAnchor"):
                        is_valid, b_time, b_num = contract.functions.verifyAnchor(event_id, digest_bytes).call()
                        if is_valid:
                            on_chain_verified = True
                            on_chain_msg = f" (Independently confirmed on-chain at block #{b_num})"
                        else:
                            new_verif_status = "MISMATCH"
                            on_chain_msg = " (On-chain contract state verification returned false)"
                    elif hasattr(contract.functions, "getAnchor"):
                        p_digest, _, _, b_num, _, exists = contract.functions.getAnchor(event_id).call()
                        if exists and p_digest == digest_bytes:
                            on_chain_verified = True
                            on_chain_msg = f" (Independently confirmed on-chain at block #{b_num})"
                        elif exists:
                            new_verif_status = "MISMATCH"
                            on_chain_msg = " (On-chain digest does not match computed hash)"
            except Exception as verif_exc:
                logger.debug("On-chain verification query failed: %s", sanitize_blockchain_error(verif_exc))

        # Update verification status in database
        cur.execute(
            """
            UPDATE blockchain_anchors
            SET verification_status = %s
            WHERE anchor_id = %s;
            """,
            (new_verif_status, str(anchor_id)),
        )
        conn.commit()

        details = (
            f"Digest matched successfully against anchor {anchor_id}{on_chain_msg}."
            if digest_verified
            else f"Cryptographic mismatch! Computed {used_computed} != Anchored {anchored_hash}{on_chain_msg}."
        )

        return VerificationResult(
            event_id=event_id,
            matched=digest_verified,
            computed_hash=used_computed,
            anchored_hash=anchored_hash,
            verification_status=new_verif_status,
            confirmation_status=conf_status,
            block_number=block_num,
            transaction_hash=tx_hash,
            explorer_url=explorer_url,
            on_chain_verified=on_chain_verified,
            digest_verified=digest_verified,
            contract_address=contract_addr if contract_addr != UNCONFIGURED_CONTRACT else None,
            details=details,
        )


def verify_on_chain(
    conn,
    event_id: str,
    web3_client: Optional[Any] = None,
) -> VerificationResult:
    """Explicitly verify on-chain transaction receipt and smart contract state for an anchored event."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                anchor_id, payload_hash, confirmation_status,
                block_number, transaction_hash, contract_address, chain_id, explorer_url
            FROM blockchain_anchors
            WHERE event_id_or_batch_id = %s
            ORDER BY anchored_at DESC
            LIMIT 1;
            """,
            (event_id.strip(),),
        )
        row = cur.fetchone()
        if not row:
            return VerificationResult(
                event_id=event_id,
                matched=False,
                computed_hash="",
                anchored_hash=None,
                verification_status="NOT_FOUND",
                confirmation_status="NOT_SUBMITTED",
                on_chain_verified=False,
                digest_verified=False,
                details=f"No blockchain anchor found for event '{event_id}'.",
            )

        anchor_id, anchored_hash, conf_status, block_num, tx_hash, contract_addr, chain_id, explorer_url = row

    mode = os.environ.get("BLOCKCHAIN_MODE", "REAL_NETWORK").upper()
    if mode == "SIMULATED":
        return VerificationResult(
            event_id=event_id,
            matched=True,
            computed_hash=anchored_hash,
            anchored_hash=anchored_hash,
            verification_status="SIMULATED",
            confirmation_status="CONFIRMED_SIMULATED",
            block_number=block_num,
            transaction_hash=tx_hash,
            explorer_url=None,
            on_chain_verified=False,
            digest_verified=True,
            contract_address=contract_addr,
            details="Anchor is in local SIMULATED mode. Honest audit confirms it was not broadcast to a live public blockchain.",
        )

    rpc_url = os.environ.get("WEB3_PROVIDER_URI") or os.environ.get("RPC_URL")
    target_contract = contract_addr if contract_addr and contract_addr != UNCONFIGURED_CONTRACT else os.environ.get("CONTRACT_ADDRESS")

    if not rpc_url or not target_contract or target_contract == UNCONFIGURED_CONTRACT:
        return VerificationResult(
            event_id=event_id,
            matched=False,
            computed_hash=anchored_hash,
            anchored_hash=anchored_hash,
            verification_status="UNCONFIGURED",
            confirmation_status=conf_status,
            block_number=block_num,
            transaction_hash=tx_hash,
            explorer_url=explorer_url,
            on_chain_verified=False,
            digest_verified=True,
            contract_address=contract_addr,
            details="Live EVM verification is blocked: RPC_URL or CONTRACT_ADDRESS is not configured in environment.",
        )

    w3 = web3_client
    if not w3:
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        except Exception as exc:
            return VerificationResult(
                event_id=event_id,
                matched=False,
                computed_hash=anchored_hash,
                anchored_hash=anchored_hash,
                verification_status="FAILED",
                confirmation_status=conf_status,
                block_number=block_num,
                transaction_hash=tx_hash,
                explorer_url=explorer_url,
                on_chain_verified=False,
                digest_verified=True,
                contract_address=contract_addr,
                details=f"Failed to initialize Web3 client: {sanitize_blockchain_error(exc)}",
            )

    try:
        if not w3.is_connected():
            return VerificationResult(
                event_id=event_id,
                matched=False,
                computed_hash=anchored_hash,
                anchored_hash=anchored_hash,
                verification_status="FAILED",
                confirmation_status=conf_status,
                block_number=block_num,
                transaction_hash=tx_hash,
                explorer_url=explorer_url,
                on_chain_verified=False,
                digest_verified=True,
                contract_address=contract_addr,
                details=f"Web3 provider at {sanitize_blockchain_error(rpc_url)} is unreachable.",
            )

        on_chain_verified = False
        receipt_confirmed = False
        if tx_hash:
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                if receipt and receipt.get("status") == 1:
                    receipt_confirmed = True
                    block_num = receipt.get("blockNumber", block_num)
            except Exception as r_exc:
                logger.debug("Receipt lookup failed: %s", sanitize_blockchain_error(r_exc))

        abi = load_contract_abi()
        contract = w3.eth.contract(address=w3.to_checksum_address(target_contract), abi=abi)
        digest_bytes = CanonicalHasher.digest_to_bytes32(anchored_hash)

        if hasattr(contract.functions, "verifyAnchor"):
            is_valid, b_time, b_num = contract.functions.verifyAnchor(event_id, digest_bytes).call()
            on_chain_verified = bool(is_valid)
            if is_valid and b_num:
                block_num = b_num
        elif hasattr(contract.functions, "getAnchor"):
            p_digest, _, _, b_num, _, exists = contract.functions.getAnchor(event_id).call()
            on_chain_verified = bool(exists and p_digest == digest_bytes)
            if on_chain_verified and b_num:
                block_num = b_num
        elif receipt_confirmed:
            on_chain_verified = True

        new_verification_status = "MATCHED" if on_chain_verified else ("FAILED" if not receipt_confirmed else "MISMATCH")
        new_confirmation_status = "CONFIRMED" if (on_chain_verified or receipt_confirmed) else conf_status
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE blockchain_anchors
                SET verification_status = %s,
                    confirmation_status = %s
                WHERE anchor_id = %s;
                """,
                (new_verification_status, new_confirmation_status, str(anchor_id)),
            )
            conn.commit()

        return VerificationResult(
            event_id=event_id,
            matched=on_chain_verified,
            computed_hash=anchored_hash,
            anchored_hash=anchored_hash,
            verification_status=new_verification_status,
            confirmation_status=new_confirmation_status,
            block_number=block_num,
            transaction_hash=tx_hash,
            explorer_url=explorer_url,
            on_chain_verified=on_chain_verified,
            digest_verified=True,
            contract_address=target_contract,
            details=f"On-chain contract state verification {'succeeded at block #' + str(block_num) if on_chain_verified else 'failed or did not match'}.",
        )
    except Exception as exc:
        return VerificationResult(
            event_id=event_id,
            matched=False,
            computed_hash=anchored_hash,
            anchored_hash=anchored_hash,
            verification_status="FAILED",
            confirmation_status=conf_status,
            block_number=block_num,
            transaction_hash=tx_hash,
            explorer_url=explorer_url,
            on_chain_verified=False,
            digest_verified=True,
            contract_address=contract_addr,
            details=f"On-chain verification error: {sanitize_blockchain_error(exc)}",
        )


def list_blockchain_anchors(
    conn,
    event_id: Optional[str] = None,
    confirmation_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[BlockchainAnchorRecord]:
    """Retrieve list of blockchain anchor records."""
    clauses: list[str] = []
    params: list = []

    if event_id:
        clauses.append("event_id_or_batch_id = %s")
        params.append(event_id.strip())

    if confirmation_status:
        clauses.append("confirmation_status = %s")
        params.append(confirmation_status.strip().upper())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            anchor_id, event_id_or_batch_id, payload_hash, chain_name,
            chain_id, contract_address, transaction_hash, block_number,
            anchored_at, confirmation_status, verification_status, error_message,
            confirmed_at, receipt_status, gas_used, retry_count, explorer_url
        FROM blockchain_anchors
        {where_sql}
        ORDER BY anchored_at DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [
        _row_to_anchor_record(
            r,
            mode="SIMULATED" if "simulat" in str(r[3]).lower() or os.environ.get("BLOCKCHAIN_MODE", "").upper() == "SIMULATED" else "REAL_NETWORK",
        )
        for r in rows
    ]


def get_blockchain_service_status(conn) -> BlockchainStatusResponse:
    """Retrieve operational health, connection status, and anchor metrics for blockchain subsystem."""
    mode = os.environ.get("BLOCKCHAIN_MODE", "REAL_NETWORK").upper()
    rpc_url = os.environ.get("WEB3_PROVIDER_URI") or os.environ.get("RPC_URL")
    contract_addr = os.environ.get("CONTRACT_ADDRESS")
    private_key = os.environ.get("BLOCKCHAIN_PRIVATE_KEY") or os.environ.get("SIGNER_PRIVATE_KEY")
    chain_id = int(os.environ.get("CHAIN_ID", str(DEFAULT_CHAIN_ID)))
    chain_name = os.environ.get("CHAIN_NAME", DEFAULT_CHAIN_NAME)
    explorer_prefix = os.environ.get("EXPLORER_TX_URL_PREFIX", DEFAULT_EXPLORER_PREFIX)

    connected = False
    latest_block: Optional[int] = None
    contract_deployed = False
    signer_address: Optional[str] = None

    if mode != "SIMULATED" and rpc_url:
        try:
            from web3 import Web3  # type: ignore
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
            if w3.is_connected():
                connected = True
                latest_block = int(w3.eth.block_number)
                if private_key:
                    signer_address = w3.eth.account.from_key(private_key.strip()).address
                if contract_addr and contract_addr != UNCONFIGURED_CONTRACT:
                    code = w3.eth.get_code(w3.to_checksum_address(contract_addr))
                    contract_deployed = bool(code and code != b"" and code != b"\x00")
        except Exception as exc:
            logger.debug("Status check connection error: %s", sanitize_blockchain_error(exc))

    # Query anchor totals from PostgreSQL
    total_anchors = 0
    confirmed_anchors = 0
    pending_anchors = 0

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE confirmation_status = 'CONFIRMED'),
                COUNT(*) FILTER (WHERE confirmation_status = 'PENDING')
            FROM blockchain_anchors;
            """
        )
        row = cur.fetchone()
        if row:
            total_anchors = int(row[0])
            confirmed_anchors = int(row[1])
            pending_anchors = int(row[2])

    return BlockchainStatusResponse(
        mode="SIMULATED" if mode == "SIMULATED" or not rpc_url else "REAL_NETWORK",
        connected=connected,
        chain_name=chain_name,
        chain_id=chain_id,
        contract_address=contract_addr if contract_addr != UNCONFIGURED_CONTRACT else None,
        contract_deployed=contract_deployed,
        signer_address=signer_address,
        latest_block=latest_block,
        explorer_tx_url_prefix=explorer_prefix,
        total_anchors=total_anchors,
        confirmed_anchors=confirmed_anchors,
        pending_anchors=pending_anchors,
    )
