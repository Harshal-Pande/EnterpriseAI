from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class InventoryItem(BaseModel):
    id: str
    inventory_id: str
    name: str
    product_name: str
    item_id: str
    product_id: str
    product_category: Optional[str] = None
    warehouse_id: str
    warehouse_name: Optional[str] = None
    warehouse_type: Optional[str] = None
    quantity: float
    on_hand_qty: float
    reserved_qty: float
    available_qty: float
    uom: str
    stock_signal: str
    status: str
    reorder_threshold: Optional[float] = None
    reorder_point_qty: Optional[float] = None
    safety_stock_qty: Optional[float] = None
    target_stock_qty: Optional[float] = None
    shortage: float = 0.0
    as_of_timestamp: Optional[str] = None


class InventorySummary(BaseModel):
    total_skus: int
    total_on_hand_qty: float
    total_available_qty: float
    total_reserved_qty: float
    normal_count: int
    low_stock_count: int
    critical_count: int
    out_of_stock_count: int
