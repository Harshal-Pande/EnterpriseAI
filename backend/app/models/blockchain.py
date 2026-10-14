"""Pydantic data models for Blockchain Audit Anchoring (Phase 7)."""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AnchorEventRequest(BaseModel):
    event_id: str = Field(..., description="Audit event UUID or batch identifier")
    payload: Dict[str, Any] = Field(..., description="Raw audit event payload to canonicalize and anchor")
    chain_name: Optional[str] = Field("ethereum-sepolia", description="Target blockchain network name")
    contract_address: Optional[str] = Field(None, description="Deployed audit anchor smart contract address")
    force_simulation: Optional[bool] = Field(False, description="Explicitly use local simulation adapter")


class BlockchainAnchorRecord(BaseModel):
    anchor_id: str
    event_id_or_batch_id: str
    payload_hash: str
    chain_name: str
    chain_id: int
    contract_address: str
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    anchored_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    receipt_status: Optional[int] = None
    gas_used: Optional[int] = None
    explorer_url: Optional[str] = None
    retry_count: Optional[int] = 0
    confirmation_status: str = Field(..., description="NOT_SUBMITTED, PENDING, CONFIRMED, or FAILED")
    verification_status: str = Field(..., description="NOT_VERIFIED, MATCHED, MISMATCH, or FAILED")
    error_message: Optional[str] = None
    mode: str = Field(..., description="REAL_NETWORK or SIMULATED")


class VerificationResult(BaseModel):
    event_id: str
    matched: bool
    computed_hash: str
    anchored_hash: Optional[str] = None
    verification_status: str
    confirmation_status: Optional[str] = None
    block_number: Optional[int] = None
    transaction_hash: Optional[str] = None
    explorer_url: Optional[str] = None
    on_chain_verified: Optional[bool] = False
    contract_address: Optional[str] = None
    details: str


class BlockchainStatusResponse(BaseModel):
    mode: str = Field(..., description="REAL_NETWORK or SIMULATED")
    connected: bool
    chain_name: str
    network_name: Optional[str] = None
    chain_id: int
    contract_address: Optional[str] = None
    contract_deployed: bool = False
    signer_address: Optional[str] = None
    signer_configured: bool = False
    rpc_configured: bool = False
    latest_block: Optional[int] = None
    explorer_tx_url_prefix: Optional[str] = None
    total_anchors: int = 0
    total_anchors_tracked: int = 0
    confirmed_anchors: int = 0
    pending_anchors: int = 0
