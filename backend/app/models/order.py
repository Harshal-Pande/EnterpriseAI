from __future__ import annotations

from typing import List, Optional
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
    created_at: Optional[str] = None
    required_delivery_at: Optional[str] = None
    total_amount: Optional[float] = 0.0
    total_quantity: Optional[float] = 0.0
    line_count: Optional[int] = 0
    lines: Optional[List[OrderLine]] = None
