"""Pydantic data models for Deterministic Policy Evaluations and Approvals."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyEvaluationRequest(BaseModel):
    action_type: str = Field(..., description="Action to evaluate, e.g. CREATE_PURCHASE_ORDER, FULFILL_ORDER")
    target_entity_id: Optional[str] = Field(None, description="Order, Supplier, or Product ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action payload parameters")
    decision_id: Optional[str] = Field(None, description="Associated decision UUID if available")
    action_id: Optional[str] = Field(None, description="Associated action UUID if available")
    scenario_id: Optional[str] = Field(None, description="Associated workflow scenario UUID if available")


class RuleEvaluationResult(BaseModel):
    rule_id: str
    domain: str
    result: str = Field(..., description="PASS, FAIL, SKIP, or NEEDS_APPROVAL")
    condition: str
    explanation: str
    details: Dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResponse(BaseModel):
    evaluation_id: str
    overall_result: str = Field(..., description="PASS, FAIL, or NEEDS_APPROVAL")
    requires_approval: bool
    applicable_rules_count: int
    rule_results: List[RuleEvaluationResult]
    policy_eval_ids: List[str] = Field(default_factory=list, description="IDs of rows persisted in policy_evaluations")
    approval_domain: Optional[str] = None
    approval_id: Optional[str] = None
    rejection_reason: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    status: str = Field(..., description="APPROVED or REJECTED")
    decided_by: str = Field(..., description="User or role authorizing this decision")
    reason: Optional[str] = Field(None, description="Audit rationale or notes")


class ApprovalRequestRecord(BaseModel):
    approval_id: str
    action_id: Optional[str] = None
    decision_id: Optional[str] = None
    scenario_id: Optional[str] = None
    requested_at: str
    required_domain: Optional[str] = None
    status: str
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    reason: Optional[str] = None
