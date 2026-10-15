from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.models.order import Order, OrderLine

logger = logging.getLogger("enterpriseai.orders")

router = APIRouter()

ALLOWED_STATUSES = {"OPEN", "IN_PROGRESS", "AT_RISK", "COMPLETED", "CANCELLED"}
ALLOWED_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
ALLOWED_SORT_FIELDS = {
    "created_at": "o.created_at",
    "order_id": "o.order_id",
    "status": "o.status",
    "priority": "o.priority",
    "customer_ref": "o.customer_ref",
    "total_amount": "total_amount",
}


@router.get("/", response_model=List[Order])
def list_orders(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by order status"),
    priority: Optional[str] = Query(None, description="Filter by order priority"),
    customer_ref: Optional[str] = Query(None, description="Filter by customer reference"),
    entity_id: Optional[str] = Query(None, description="Filter by entity / destination ID"),
    limit: int = Query(50, ge=1, le=500, description="Maximum orders to return"),
    offset: int = Query(0, ge=0, description="Number of orders to skip"),
    sort_by: str = Query("created_at", description="Sort field (created_at, order_id, status, priority, customer_ref)"),
    sort_order: str = Query("desc", description="Sort direction (asc or desc)"),
    conn=Depends(get_db),
):
    """Retrieve orders from PostgreSQL with filtering, pagination, and calculated totals."""
    # Validate sort field and direction against safe whitelist
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

    # Validate status and priority filters if provided
    clauses: list[str] = []
    params: list = []

    if status_filter:
        norm_status = status_filter.upper().replace(" ", "_")
        if norm_status not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid order status: {status_filter}. Allowed values: {sorted(ALLOWED_STATUSES)}",
            )
        clauses.append("o.status = %s")
        params.append(norm_status)

    if priority:
        norm_priority = priority.upper()
        if norm_priority not in ALLOWED_PRIORITIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {priority}. Allowed values: {sorted(ALLOWED_PRIORITIES)}",
            )
        clauses.append("o.priority = %s")
        params.append(norm_priority)

    if customer_ref:
        clauses.append("o.customer_ref ILIKE %s")
        params.append(f"%{customer_ref}%")

    if entity_id:
        clauses.append("o.entity_id = %s")
        params.append(entity_id)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_column = ALLOWED_SORT_FIELDS[sort_by_lower]

    sql = f"""
        SELECT
            o.order_id,
            o.customer_ref,
            o.entity_id,
            o.status,
            o.priority,
            o.currency,
            o.external_reference,
            o.created_at,
            o.required_delivery_at,
            COALESCE(SUM(ol.requested_qty * ol.unit_price_inr), 0) AS total_amount,
            COALESCE(SUM(ol.requested_qty), 0) AS total_quantity,
            COUNT(ol.order_line_id) AS line_count
        FROM orders o
        LEFT JOIN order_lines ol ON o.order_id = ol.order_id
        {where_sql}
        GROUP BY
            o.order_id,
            o.customer_ref,
            o.entity_id,
            o.status,
            o.priority,
            o.currency,
            o.external_reference,
            o.created_at,
            o.required_delivery_at
        ORDER BY {order_column} {sort_order_upper}, o.order_id {sort_order_upper}
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("Database query failed in list_orders: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving orders",
        ) from exc

    results: list[Order] = []
    for r in rows:
        results.append(
            Order(
                id=r[0],
                order_id=r[0],
                customer_id=r[1],
                customer_ref=r[1],
                customer=r[1],
                entity_id=r[2],
                destination=r[2],
                status=r[3],
                priority=r[4],
                currency=r[5],
                external_reference=r[6],
                created_at=r[7].isoformat() if r[7] else None,
                required_delivery_at=r[8].isoformat() if r[8] else None,
                total_amount=float(r[9]) if r[9] is not None else 0.0,
                total_quantity=float(r[10]) if r[10] is not None else 0.0,
                line_count=int(r[11]) if r[11] is not None else 0,
            )
        )
    return results


@router.get("/summary")
def get_orders_summary(conn=Depends(get_db)):
    """Retrieve operational orders aggregation summary."""
    sql = """
        SELECT
            COUNT(*) AS total_orders,
            COUNT(*) FILTER (WHERE status IN ('OPEN', 'IN_PROGRESS', 'CONFIRMED', 'PROCESSING')) AS processing_count,
            COUNT(*) FILTER (WHERE status IN ('COMPLETED', 'SHIPPED', 'DELIVERED')) AS completed_count,
            COUNT(*) FILTER (WHERE status IN ('AT_RISK', 'EXCEPTION', 'CANCELLED')) AS exception_count
        FROM orders;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            r = cur.fetchone()
            return {
                "total_orders": int(r[0]) if r and r[0] is not None else 0,
                "processing_count": int(r[1]) if r and r[1] is not None else 0,
                "completed_count": int(r[2]) if r and r[2] is not None else 0,
                "exception_count": int(r[3]) if r and r[3] is not None else 0,
            }
    except Exception as exc:
        logger.error("Database query failed in get_orders_summary: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving orders summary",
        ) from exc


@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str, conn=Depends(get_db)):
    """Retrieve a single order by ID along with its constituent order lines."""
    order_sql = """
        SELECT
            o.order_id,
            o.customer_ref,
            o.entity_id,
            o.status,
            o.priority,
            o.currency,
            o.external_reference,
            o.created_at,
            o.required_delivery_at,
            COALESCE(SUM(ol.requested_qty * ol.unit_price_inr), 0) AS total_amount,
            COALESCE(SUM(ol.requested_qty), 0) AS total_quantity,
            COUNT(ol.order_line_id) AS line_count
        FROM orders o
        LEFT JOIN order_lines ol ON o.order_id = ol.order_id
        WHERE o.order_id = %s
        GROUP BY
            o.order_id,
            o.customer_ref,
            o.entity_id,
            o.status,
            o.priority,
            o.currency,
            o.external_reference,
            o.created_at,
            o.required_delivery_at;
    """

    lines_sql = """
        SELECT
            ol.order_line_id,
            ol.product_id,
            p.product_name,
            p.product_category,
            ol.requested_qty,
            ol.unit_price_inr,
            ol.uom,
            (ol.requested_qty * ol.unit_price_inr) AS line_total_inr
        FROM order_lines ol
        JOIN products p ON ol.product_id = p.product_id
        WHERE ol.order_id = %s
        ORDER BY ol.order_line_id;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(order_sql, (order_id,))
            order_row = cur.fetchone()
            if not order_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Order {order_id} not found",
                )

            cur.execute(lines_sql, (order_id,))
            line_rows = cur.fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database query failed in get_order: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving order details",
        ) from exc

    lines = [
        OrderLine(
            order_line_id=lr[0],
            product_id=lr[1],
            product_name=lr[2],
            product_category=lr[3],
            requested_qty=float(lr[4]) if lr[4] is not None else 0.0,
            unit_price_inr=float(lr[5]) if lr[5] is not None else 0.0,
            uom=lr[6],
            line_total_inr=float(lr[7]) if lr[7] is not None else 0.0,
        )
        for lr in line_rows
    ]

    return Order(
        id=order_row[0],
        order_id=order_row[0],
        customer_id=order_row[1],
        customer_ref=order_row[1],
        customer=order_row[1],
        entity_id=order_row[2],
        destination=order_row[2],
        status=order_row[3],
        priority=order_row[4],
        currency=order_row[5],
        external_reference=order_row[6],
        created_at=order_row[7].isoformat() if order_row[7] else None,
        required_delivery_at=order_row[8].isoformat() if order_row[8] else None,
        total_amount=float(order_row[9]) if order_row[9] is not None else 0.0,
        total_quantity=float(order_row[10]) if order_row[10] is not None else 0.0,
        line_count=int(order_row[11]) if order_row[11] is not None else 0,
        lines=lines,
    )


@router.post("/")
def create_order(order_data: dict):
    """Starter implementation for order creation (preserved as-is)."""
    return {"status": "created", "order_id": "ORD-1043"}


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: str,
    payload: dict,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Transition an order through its lifecycle state machine."""
    from app.services.order_service import transition_order_status

    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'status' is required in payload.",
        )

    reason = payload.get("reason")
    actor_id = payload.get("actor_id", "operator")
    return transition_order_status(conn, order_id, new_status, reason=reason, actor_id=actor_id)

