"""Typed schema contracts for specialist agents (Supervisor, Inventory, Procurement, Finance, Logistics).

Ensures deterministic structured input and output contracts across all specialist agents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InventoryOutput(BaseModel):
    item_id: str
    warehouse_id: Optional[str] = None
    on_hand_qty: float
    reserved_qty: float
    available_qty: float
    requested_qty: float
    shortage_qty: float
    stock_status: str = Field(..., description="OK, LOW_STOCK, REORDER_REQUIRED, or SHORTAGE")
    reorder_point_qty: Optional[float] = None
    safety_stock_qty: Optional[float] = None
    action_required: str
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)


class ProcurementOutput(BaseModel):
    item_id: str
    required_qty: float
    selected_supplier_id: Optional[str] = None
    selected_supplier_name: Optional[str] = None
    selected_offer_id: Optional[str] = None
    unit_price_inr: Optional[float] = None
    estimated_cost: float
    lead_time_hours: Optional[int] = None
    suppliers_evaluated_count: int
    procurement_status: str = Field(..., description="SUPPLIER_SELECTED, NO_ACTIVE_OFFERS, or SHORTAGE_COVERED")
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)


class FinanceOutput(BaseModel):
    budget_id: Optional[str] = None
    cost_center: Optional[str] = None
    estimated_spend: float
    available_budget: float
    threshold_limit: float
    finance_status: str = Field(..., description="APPROVED, NEEDS_APPROVAL, or BUDGET_EXCEEDED")
    requires_approval: bool
    budget_allocated: bool
    reason: str
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)


class LogisticsOutput(BaseModel):
    route_id: str
    origin_warehouse_id: Optional[str] = None
    destination: str
    transit_days: int
    estimated_delivery: str
    logistics_status: str = Field(..., description="FEASIBLE, DELAYED, or BLOCKED")
    carrier_score: Optional[float] = None
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)


class SupervisorOutput(BaseModel):
    workflow_id: str
    order_id: str
    current_agent: str
    status: str
    decision_code: str
    summary: str
    human_approval_required: bool
    recommended_action: Dict[str, Any]
    specialists_invoked: List[str]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)
