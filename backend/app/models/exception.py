"""Pydantic data models for Unified Operational Exceptions and Resolution Lifecycle."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OperationalException(BaseModel):
    exception_id: str
    order_id: Optional[str] = None
    scenario_id: Optional[str] = None
    workflow_run_id: Optional[str] = None
    decision_id: Optional[str] = None
    action_id: Optional[str] = None
    approval_id: Optional[str] = None
    severity: str
    exception_type: str
    cause: str
    owner_role: str
    status: str
    ai_recommendation: Dict[str, Any] = Field(default_factory=dict)
    proposed_action: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    order_details: Optional[Dict[str, Any]] = None
    action_details: Optional[Dict[str, Any]] = None
    approval_details: Optional[Dict[str, Any]] = None


class OperationalExceptionSummary(BaseModel):
    exception_id: str
    order_id: Optional[str] = None
    severity: str
    exception_type: str
    cause: str
    owner_role: str
    status: str
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    customer_ref: Optional[str] = None
    entity_id: Optional[str] = None


class ExceptionActionProposeRequest(BaseModel):
    action_type: str = Field(..., description="Action type to propose (e.g. CREATE_PURCHASE_ORDER, ALLOCATE_INVENTORY, RESOLVE_DISRUPTION)")
    target_entity_id: Optional[str] = Field(None, description="Target entity identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action payload parameters")
    justification: Optional[str] = Field(None, description="Operator justification for the proposed action")
    notes: Optional[str] = Field(None, description="Operator resolution notes")


class ExceptionApprovalRequest(BaseModel):
    decision: str = Field(..., description="APPROVED or REJECTED")
    justification: str = Field(..., min_length=3, description="Mandatory operator audit justification")


class ExceptionResolutionResponse(BaseModel):
    exception_id: str
    status: str
    order_id: Optional[str] = None
    order_status: Optional[str] = None
    action_id: Optional[str] = None
    action_status: Optional[str] = None
    message: str


class ExceptionResumeRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Optional notes on manual exception resolution")

