from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OrderLine(BaseModel):
    order_line_id: str
    product_id: str
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    requested_qty: float
    unit_price_inr: Optional[float] = None
    uom: str
    line_total_inr: Optional[float] = None


class Order(BaseModel):
    id: str
    order_id: str
    customer_id: str
    customer_ref: str
    customer: Optional[str] = None
    status: str
    priority: str
    entity_id: str
    destination: Optional[str] = None
    currency: str = "INR"
    external_reference: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: Optional[str] = None
    required_delivery_at: Optional[str] = None
    total_amount: Optional[float] = 0.0
    total_quantity: Optional[float] = 0.0
    line_count: Optional[int] = 0
    lines: Optional[List[OrderLine]] = None


class OrderLineCreateRequest(BaseModel):
    product_id: str = Field(..., description="Valid product ID from products master table")
    requested_qty: float = Field(..., gt=0, description="Order quantity (must be positive)")
    unit_price_inr: Optional[float] = Field(None, gt=0, description="Optional custom unit price in INR")
    uom: Optional[str] = Field("MT", description="Unit of measurement (defaults to MT)")


class OrderCreateRequest(BaseModel):
    customer_ref: str = Field(..., min_length=1, max_length=200, description="Customer or project reference name")
    entity_id: str = Field(..., description="Origin or destination operating entity ID")
    priority: str = Field("MEDIUM", description="Order priority: LOW, MEDIUM, HIGH, CRITICAL")
    required_delivery_at: Optional[str] = Field(None, description="ISO datetime for required customer delivery")
    currency: str = Field("INR", description="Order currency code")
    external_reference: Optional[str] = Field(None, description="External ERP PO or requisition reference")
    idempotency_key: Optional[str] = Field(None, description="Unique client idempotency token to prevent duplicate creation on retry")
    lines: List[OrderLineCreateRequest] = Field(..., min_length=1, description="One or more constituent order lines")
    auto_enqueue: bool = Field(True, description="Whether order should automatically enter processing queue")


class OrderQueueItem(BaseModel):
    queue_id: str
    order_id: str
    queue_position: int
    status: str
    enqueued_at: str
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    attempt_count: int = 0
    last_error: Optional[str] = None
    exception_id: Optional[str] = None
    origin: str = "SYSTEM"
    order: Optional[Order] = None


class OrderQueueStatusResponse(BaseModel):
    total_queued: int
    processing_count: int
    waiting_exception_count: int
    completed_count: int
    total_orders_tracked: int
    runner_enabled: bool
    runner_interval_seconds: int
    runner_status: str
    next_eligible_run_time: Optional[str] = None
    current_claimed_order_id: Optional[str] = None


class OrderCreateResponse(BaseModel):
    status: str = "created"
    order_id: str
    queue_position: Optional[int] = None
    queue_id: Optional[str] = None
    enqueued: bool = True
    order: Order
