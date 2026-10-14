from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class SupplierContractSummary(BaseModel):
    contract_id: str
    contract_category: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    contract_limit_inr: Optional[float] = None
    currency: str = "INR"
    status: str
    owner_department: Optional[str] = None


class SupplierOfferSummary(BaseModel):
    offer_id: str
    item_id: str
    unit_price_inr: float
    price_uom: str
    lead_time_hours: Optional[int] = None
    max_available_qty: Optional[float] = None
    on_time_rate: Optional[float] = None
    offer_status: str


class Supplier(BaseModel):
    id: str
    supplier_id: str
    name: str
    supplier_name: str
    supplier_category: str
    category: Optional[str] = None
    status: str
    risk_band: str
    historical_on_time_rate: Optional[float] = None
    reliability_score: float
    score: float
    default_lead_time_hours: Optional[int] = None
    delivery_days: Optional[float] = None
    deliveryDays: Optional[float] = None
    price_per_unit: Optional[float] = None
    pricePerUnit: Optional[float] = None
    availability: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    contracts_count: int = 0
    offers_count: int = 0
    contracts: Optional[List[SupplierContractSummary]] = None
    offers: Optional[List[SupplierOfferSummary]] = None
