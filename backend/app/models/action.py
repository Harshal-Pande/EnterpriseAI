"""Pydantic data models for Controlled Action Execution (Task 11)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ActionProposeRequest(BaseModel):
    scenario_id: str = Field(..., description="Parent workflow scenario UUID")
    decision_id: Optional[str] = Field(None, description="Parent decision UUID if available")
    action_type: str = Field(..., description="Action type: CREATE_PURCHASE_ORDER, ALLOCATE_INVENTORY, DISPATCH_SHIPMENT")
    target_entity_id: Optional[str] = Field(None, description="Target entity identifier (order_id, supplier_id, etc.)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action payload parameters")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key to prevent duplicate action proposal")


class ActionRecord(BaseModel):
    action_id: str
    scenario_id: str
    decision_id: Optional[str] = None
    action_type: str
    target_entity_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str
    requires_approval: bool
    approved_by: Optional[str] = None
    created_at: str
    executed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    idempotency_key: str


class ActionExecutionResultRecord(BaseModel):
    execution_id: str
    action_id: str
    attempted_at: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ActionDetailResponse(BaseModel):
    action: ActionRecord
    execution_history: List[ActionExecutionResultRecord] = Field(default_factory=list)
