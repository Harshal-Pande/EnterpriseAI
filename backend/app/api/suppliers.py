from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import get_db
from app.models.supplier import (
    Supplier,
    SupplierContractSummary,
    SupplierOfferSummary,
)

logger = logging.getLogger("enterpriseai.suppliers")

router = APIRouter()

ALLOWED_STATUSES = {"ACTIVE", "INACTIVE", "SUSPENDED"}
ALLOWED_RISK_BANDS = {"LOW", "MEDIUM", "HIGH"}
ALLOWED_SORT_FIELDS = {
    "supplier_id": "s.supplier_id",
    "id": "s.supplier_id",
    "supplier_name": "s.supplier_name",
    "name": "s.supplier_name",
    "supplier_category": "s.supplier_category",
    "category": "s.supplier_category",
    "status": "s.status",
    "risk_band": "s.risk_band",
    "historical_on_time_rate": "s.historical_on_time_rate",
    "reliability_score": "s.historical_on_time_rate",
    "score": "s.historical_on_time_rate",
    "default_lead_time_hours": "s.default_lead_time_hours",
}


@router.get("/", response_model=List[Supplier])
def list_suppliers(
    category: Optional[str] = Query(None, description="Filter by supplier category"),
    supplier_category: Optional[str] = Query(None, description="Filter by supplier category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ACTIVE, INACTIVE, SUSPENDED)"),
    risk_band: Optional[str] = Query(None, description="Filter by risk band (LOW, MEDIUM, HIGH)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum suppliers to return"),
    offset: int = Query(0, ge=0, description="Number of suppliers to skip"),
    sort_by: str = Query("supplier_id", description="Sort field"),
    sort_order: str = Query("asc", description="Sort direction (asc or desc)"),
    conn=Depends(get_db),
):
    """Retrieve suppliers with parameterized filtering, safe sorting, and joined contracts/offers aggregates."""
    effective_category = category or supplier_category
    sort_by_lower = sort_by.lower()
    if sort_by_lower not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field: {sort_by}. Allowed fields: {list(ALLOWED_SORT_FIELDS.keys())}",
        )

    sort_order_upper = sort_order.upper()
    if sort_order_upper not in {"ASC", "DESC"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_order: {sort_order}. Must be 'asc' or 'desc'.",
        )

    clauses: list[str] = []
    params: list = []

    if effective_category:
        clauses.append("s.supplier_category ILIKE %s")
        params.append(f"%{effective_category}%")

    if status_filter:
        norm_status = status_filter.upper().replace(" ", "_")
        if norm_status not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid supplier status: {status_filter}. Allowed values: {sorted(ALLOWED_STATUSES)}",
            )
        clauses.append("s.status = %s")
        params.append(norm_status)

    if risk_band:
        norm_risk = risk_band.upper()
        if norm_risk not in ALLOWED_RISK_BANDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_band: {risk_band}. Allowed values: {sorted(ALLOWED_RISK_BANDS if 'ALLOWED_RISB_BANDS' in locals() else ALLOWED_RISK_BANDS)}",
            )
        clauses.append("s.risk_band = %s")
        params.append(norm_risk)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_column = ALLOWED_SORT_FIELDS[sort_by_lower]

    sql = f"""
        SELECT
            s.supplier_id,
            s.supplier_name,
            s.supplier_category,
            s.status,
            s.risk_band,
            s.historical_on_time_rate,
            s.default_lead_time_hours,
            s.created_at,
            s.updated_at,
            COUNT(DISTINCT c.contract_id) AS contracts_count,
            COUNT(DISTINCT o.offer_id) AS offers_count,
            AVG(o.unit_price_inr) AS avg_unit_price,
            COALESCE(SUM(o.max_available_qty), 0) AS total_available_qty
        FROM suppliers s
        LEFT JOIN supplier_contracts c ON s.supplier_id = c.supplier_id
        LEFT JOIN supplier_offers o ON s.supplier_id = o.supplier_id
        {where_sql}
        GROUP BY s.supplier_id, s.supplier_name, s.supplier_category, s.status, s.risk_band, s.historical_on_time_rate, s.default_lead_time_hours, s.created_at, s.updated_at
        ORDER BY {order_column} {sort_order_upper}, s.supplier_id {sort_order_upper}
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("Database query failed in list_suppliers: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving suppliers",
        ) from exc

    results: list[Supplier] = []
    for r in rows:
        on_time = float(r[5]) if r[5] is not None else None
        rel_score = round(on_time * 100.0, 2) if on_time is not None else 0.0
        lead_hours = r[6]
        delivery_days = round(lead_hours / 24.0, 1) if lead_hours is not None else None
        avg_price = float(r[11]) if r[11] is not None else None
        avail_qty = float(r[12]) if r[12] is not None else 0.0

        results.append(
            Supplier(
                id=r[0],
                supplier_id=r[0],
                name=r[1],
                supplier_name=r[1],
                supplier_category=r[2],
                category=r[2],
                status=r[3],
                risk_band=r[4],
                historical_on_time_rate=on_time,
                reliability_score=rel_score,
                score=rel_score,
                default_lead_time_hours=lead_hours,
                delivery_days=delivery_days,
                deliveryDays=delivery_days,
                price_per_unit=avg_price,
                pricePerUnit=avg_price,
                availability=avail_qty,
                notes=f"Risk Band: {r[4]}. Historical On-Time Rate: {rel_score}%. Lead Time: {lead_hours}h.",
                created_at=r[7].isoformat() if r[7] else None,
                updated_at=r[8].isoformat() if r[8] else None,
                contracts_count=int(r[9]),
                offers_count=int(r[10]),
            )
        )
    return results


@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier_detail(supplier_id: str, conn=Depends(get_db)):
    """Retrieve detailed supplier profile along with related contracts and active offers."""
    sql_header = """
        SELECT
            s.supplier_id,
            s.supplier_name,
            s.supplier_category,
            s.status,
            s.risk_band,
            s.historical_on_time_rate,
            s.default_lead_time_hours,
            s.created_at,
            s.updated_at
        FROM suppliers s
        WHERE s.supplier_id = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql_header, (supplier_id,))
            r = cur.fetchone()
            if not r:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Supplier {supplier_id} not found",
                )

            # Fetch contracts
            cur.execute(
                """
                SELECT
                    contract_id,
                    contract_category,
                    effective_from,
                    effective_to,
                    contract_limit_inr,
                    currency,
                    status,
                    owner_department
                FROM supplier_contracts
                WHERE supplier_id = %s
                ORDER BY contract_id ASC;
                """,
                (supplier_id,),
            )
            c_rows = cur.fetchall()

            # Fetch offers
            cur.execute(
                """
                SELECT
                    offer_id,
                    item_id,
                    unit_price_inr,
                    price_uom,
                    lead_time_hours,
                    max_available_qty,
                    on_time_rate,
                    offer_status
                FROM supplier_offers
                WHERE supplier_id = %s
                ORDER BY offer_id ASC;
                """,
                (supplier_id,),
            )
            o_rows = cur.fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database query failed in get_supplier_detail: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving supplier details",
        ) from exc

    on_time = float(r[5]) if r[5] is not None else None
    rel_score = round(on_time * 100.0, 2) if on_time is not None else 0.0
    lead_hours = r[6]
    delivery_days = round(lead_hours / 24.0, 1) if lead_hours is not None else None

    contracts = [
        SupplierContractSummary(
            contract_id=cr[0],
            contract_category=cr[1],
            effective_from=cr[2].isoformat() if cr[2] else None,
            effective_to=cr[3].isoformat() if cr[3] else None,
            contract_limit_inr=float(cr[4]) if cr[4] is not None else None,
            currency=cr[5] or "INR",
            status=cr[6],
            owner_department=cr[7],
        )
        for cr in c_rows
    ]

    offers = [
        SupplierOfferSummary(
            offer_id=orow[0],
            item_id=orow[1],
            unit_price_inr=float(orow[2]),
            price_uom=orow[3],
            lead_time_hours=orow[4],
            max_available_qty=float(orow[5]) if orow[5] is not None else None,
            on_time_rate=float(orow[6]) if orow[6] is not None else None,
            offer_status=orow[7],
        )
        for orow in o_rows
    ]

    avg_price = (
        round(sum(o.unit_price_inr for o in offers) / len(offers), 2)
        if offers
        else None
    )
    total_avail = sum(o.max_available_qty or 0.0 for o in offers)

    return Supplier(
        id=r[0],
        supplier_id=r[0],
        name=r[1],
        supplier_name=r[1],
        supplier_category=r[2],
        category=r[2],
        status=r[3],
        risk_band=r[4],
        historical_on_time_rate=on_time,
        reliability_score=rel_score,
        score=rel_score,
        default_lead_time_hours=lead_hours,
        delivery_days=delivery_days,
        deliveryDays=delivery_days,
        price_per_unit=avg_price,
        pricePerUnit=avg_price,
        availability=total_avail,
        notes=f"Risk Band: {r[4]}. Historical On-Time Rate: {rel_score}%. Lead Time: {lead_hours}h.",
        created_at=r[7].isoformat() if r[7] else None,
        updated_at=r[8].isoformat() if r[8] else None,
        contracts_count=len(contracts),
        offers_count=len(offers),
        contracts=contracts,
        offers=offers,
    )
