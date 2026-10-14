from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel


class AuditEvent(BaseModel):
    event_id: str
    eventId: Optional[str] = None
    event_type: str
    event: Optional[str] = None
    type: Optional[str] = None
    timestamp: str
    event_timestamp: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    order_id: Optional[str] = None
    orderId: Optional[str] = None
    actor_type: Optional[str] = None
    actor_id: Optional[str] = None
    actor: Optional[str] = None
    status: str
    blockchain_status: str
    block_number: Optional[int] = None
    blockNumber: Optional[int] = None
    tx_hash: Optional[str] = None
    txHash: Optional[str] = None
    details: Optional[str] = None
    note: Optional[str] = None
    reason_code: Optional[str] = None
    evidence_refs: Optional[List[Any]] = None
    payload_hash: Optional[str] = None
    previous_event_hash: Optional[str] = None
    source_channel: Optional[str] = None
    scenario_id: Optional[str] = None
    workflow_run_id: Optional[str] = None
    explorer_url: Optional[str] = None
    explorerUrl: Optional[str] = None
    confirmed_at: Optional[str] = None
    confirmedAt: Optional[str] = None
    receipt_status: Optional[int] = None
