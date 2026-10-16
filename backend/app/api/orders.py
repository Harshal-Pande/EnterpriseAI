from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.models.order import (
    Order,
    OrderCreateRequest,
    OrderCreateResponse,
    OrderLine,
    OrderQueueItem,
    OrderQueueStatusResponse,
)
from app.services.order_queue_runner import default_order_queue_runner

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


def _fetch_order_by_id(cur, order_id: str) -> Optional[Order]:
    """Helper to fetch a fully assembled Order model with lines and calculated totals."""
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
    cur.execute(order_sql, (order_id,))
    order_row = cur.fetchone()
    if not order_row:
        return None

    cur.execute(lines_sql, (order_id,))
    line_rows = cur.fetchall()

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


@router.get("/history", response_model=List[Order])
def get_processed_history(
    limit: int = Query(100, ge=1, le=100, description="Maximum historical orders (capped at 100)"),
    conn=Depends(get_db),
):
    """Retrieve capped history of up to 100 most recent completed/processed orders."""
    # Strict 100-cap enforced as per Requirement A
    effective_limit = min(limit, 100)
    sql = """
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
        WHERE o.status = 'COMPLETED'
        GROUP BY
            o.order_id,
            o.customer_ref,
            o.entity_id,
            o.status,
            o.priority,
            o.currency,
            o.external_reference,
            o.created_at,
            o.required_delivery_at,
            o.updated_at
        ORDER BY o.updated_at DESC, o.order_id DESC
        LIMIT %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (effective_limit,))
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("Database query failed in get_processed_history: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving order history",
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


@router.get("/queue", response_model=List[OrderQueueItem])
def get_order_queue(
    status_filter: Optional[str] = Query("QUEUED", alias="status", description="Filter queue status (QUEUED, PROCESSING, WAITING_EXCEPTION, COMPLETED, ALL)"),
    limit: int = Query(100, ge=1, le=500, description="Items to return"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    conn=Depends(get_db),
):
    """Retrieve ordered items from the dedicated PostgreSQL order_processing_queue."""
    clauses: list[str] = []
    params: list = []

    if status_filter and status_filter.upper() != "ALL":
        norm_status = status_filter.upper().strip()
        clauses.append("q.status = %s")
        params.append(norm_status)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            q.queue_id,
            q.order_id,
            q.queue_position,
            q.status,
            q.enqueued_at,
            q.claimed_at,
            q.completed_at,
            q.attempt_count,
            q.last_error,
            q.exception_id,
            q.origin,
            o.customer_ref,
            o.entity_id,
            o.status AS order_status,
            o.priority,
            o.currency,
            o.external_reference,
            o.created_at,
            o.required_delivery_at,
            COALESCE(SUM(ol.requested_qty * ol.unit_price_inr), 0) AS total_amount,
            COALESCE(SUM(ol.requested_qty), 0) AS total_quantity,
            COUNT(ol.order_line_id) AS line_count
        FROM order_processing_queue q
        JOIN orders o ON q.order_id = o.order_id
        LEFT JOIN order_lines ol ON o.order_id = ol.order_id
        {where_sql}
        GROUP BY
            q.queue_id,
            q.order_id,
            q.queue_position,
            q.status,
            q.enqueued_at,
            q.claimed_at,
            q.completed_at,
            q.attempt_count,
            q.last_error,
            q.exception_id,
            q.origin,
            o.customer_ref,
            o.entity_id,
            o.status,
            o.priority,
            o.currency,
            o.external_reference,
            o.created_at,
            o.required_delivery_at
        ORDER BY
            CASE WHEN q.status = 'QUEUED' THEN q.queue_position ELSE 999999 END ASC,
            q.enqueued_at DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("Database query failed in get_order_queue: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving order queue",
        ) from exc

    results: list[OrderQueueItem] = []
    for r in rows:
        order_model = Order(
            id=r[1],
            order_id=r[1],
            customer_id=r[11],
            customer_ref=r[11],
            customer=r[11],
            entity_id=r[12],
            destination=r[12],
            status=r[13],
            priority=r[14],
            currency=r[15],
            external_reference=r[16],
            created_at=r[17].isoformat() if r[17] else None,
            required_delivery_at=r[18].isoformat() if r[18] else None,
            total_amount=float(r[19]) if r[19] is not None else 0.0,
            total_quantity=float(r[20]) if r[20] is not None else 0.0,
            line_count=int(r[21]) if r[21] is not None else 0,
        )

        results.append(
            OrderQueueItem(
                queue_id=str(r[0]),
                order_id=r[1],
                queue_position=int(r[2]),
                status=r[3],
                enqueued_at=r[4].isoformat() if r[4] else "",
                claimed_at=r[5].isoformat() if r[5] else None,
                completed_at=r[6].isoformat() if r[6] else None,
                attempt_count=int(r[7]),
                last_error=r[8],
                exception_id=str(r[9]) if r[9] else None,
                origin=r[10],
                order=order_model,
            )
        )
    return results


@router.get("/queue/status", response_model=OrderQueueStatusResponse)
def get_queue_status(conn=Depends(get_db)):
    """Retrieve operational queue status metrics and sequential runner state."""
    st = default_order_queue_runner.get_status(conn)
    return OrderQueueStatusResponse(
        total_queued=st["total_queued"],
        processing_count=st["processing_count"],
        waiting_exception_count=st["waiting_exception_count"],
        completed_count=st["completed_count"],
        total_orders_tracked=st["total_orders_tracked"],
        runner_enabled=st["runner_enabled"],
        runner_interval_seconds=st["runner_interval_seconds"],
        runner_status=st["runner_status"],
        next_eligible_run_time=st["next_eligible_run_time"],
        current_claimed_order_id=st["locked_by"],
    )


@router.get("/queue/runner/status")
def get_queue_runner_status(conn=Depends(get_db)) -> Dict[str, Any]:
    """Retrieve detailed operational runner configuration, lease status, and next scheduled run."""
    return default_order_queue_runner.get_status(conn)


@router.post("/queue/runner/start", status_code=status.HTTP_200_OK)
def start_queue_runner(
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    """Enable and start the sequential order queue runner."""
    default_order_queue_runner.resume(conn)
    default_order_queue_runner.start()
    return {"status": "RUNNING", "message": "Order queue runner resumed and loop started"}


@router.post("/queue/runner/pause", status_code=status.HTTP_200_OK)
def pause_queue_runner(
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    """Pause the sequential order queue runner."""
    default_order_queue_runner.pause(conn)
    return {"status": "PAUSED", "message": "Order queue runner paused"}


@router.post("/queue/runner/resume", status_code=status.HTTP_200_OK)
def resume_queue_runner(
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    """Resume the sequential order queue runner."""
    default_order_queue_runner.resume(conn)
    default_order_queue_runner.start()
    return {"status": "RUNNING", "message": "Order queue runner resumed"}


@router.post("/queue/runner/stop", status_code=status.HTTP_200_OK)
def stop_queue_runner(
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    """Stop the background runner task."""
    default_order_queue_runner.stop()
    return {"status": "STOPPED", "message": "Order queue runner background loop stopped"}


@router.post("/queue/runner/process-next", status_code=status.HTTP_200_OK)
def process_next_order_now(
    force: bool = Query(False, description="Process immediately even if runner is paused or off-schedule"),
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    """Execute the next queued order immediately."""
    result = default_order_queue_runner.process_next_order(conn, force=force, actor_id=current_user.user_id)
    return result


@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str, conn=Depends(get_db)):
    """Retrieve a single order by ID along with its constituent order lines."""
    try:
        with conn.cursor() as cur:
            order = _fetch_order_by_id(cur, order_id)
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Order {order_id} not found",
                )
            return order
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database query failed in get_order: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving order details",
        ) from exc


@router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Create a new manual order transactionally with lines and queue entry."""
    # 1. Validate priority
    norm_priority = payload.priority.strip().upper()
    if norm_priority not in ALLOWED_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority '{payload.priority}'. Allowed values: {sorted(ALLOWED_PRIORITIES)}",
        )

    # 2. Validate customer reference
    cust_ref = payload.customer_ref.strip()
    if not cust_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'customer_ref' cannot be empty.",
        )

    # 3. Validate entity_id foreign key
    ent_id = payload.entity_id.strip()

    # 4. Validate lines
    if not payload.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one line item.",
        )

    now = datetime.now(timezone.utc)
    req_delivery = None
    if payload.required_delivery_at:
        try:
            req_delivery = datetime.fromisoformat(payload.required_delivery_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ISO datetime format for 'required_delivery_at': {payload.required_delivery_at}",
            )

    try:
        with conn.cursor() as cur:
            # Foreign key check for entity_id
            cur.execute("SELECT entity_id FROM entities WHERE entity_id = %s;", (ent_id,))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entity '{ent_id}' does not exist in operating entities master table.",
                )

            # Validate each product_id in lines
            validated_lines = []
            for idx, line in enumerate(payload.lines):
                p_id = line.product_id.strip()
                if line.requested_qty <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Line {idx + 1}: requested_qty must be greater than zero.",
                    )

                cur.execute(
                    "SELECT base_uom, reference_unit_cost_inr FROM products WHERE product_id = %s;",
                    (p_id,),
                )
                prod_row = cur.fetchone()
                if not prod_row:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product '{p_id}' in line {idx + 1} does not exist in products master table.",
                    )

                uom = (line.uom or prod_row[0] or "MT").strip()
                unit_price = line.unit_price_inr if line.unit_price_inr is not None else float(prod_row[1] or 50000.0)
                if unit_price <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Line {idx + 1}: unit_price_inr must be greater than zero.",
                    )

                validated_lines.append({
                    "product_id": p_id,
                    "requested_qty": line.requested_qty,
                    "unit_price_inr": unit_price,
                    "uom": uom,
                })

            # Safe order ID generation: find highest numeric suffix
            cur.execute(
                """
                SELECT COALESCE(MAX(CAST(SUBSTRING(order_id FROM 5) AS INTEGER)), 1241)
                FROM orders
                WHERE order_id ~ '^ORD-[0-9]+$';
                """
            )
            max_num = cur.fetchone()[0]
            new_order_id = f"ORD-{max_num + 1}"

            # Insert into orders table
            cur.execute(
                """
                INSERT INTO orders (
                    order_id, customer_ref, entity_id, status, priority,
                    currency, external_reference, created_at, required_delivery_at, updated_at
                )
                VALUES (%s, %s, %s, 'OPEN', %s, %s, %s, %s, %s, %s);
                """,
                (
                    new_order_id,
                    cust_ref,
                    ent_id,
                    norm_priority,
                    payload.currency or "INR",
                    payload.external_reference,
                    now,
                    req_delivery,
                    now,
                ),
            )

            # Insert order lines
            for l_idx, vl in enumerate(validated_lines):
                line_id = f"LN-{new_order_id}-{l_idx + 1:02d}"
                cur.execute(
                    """
                    INSERT INTO order_lines (
                        order_line_id, order_id, product_id, requested_qty,
                        unit_price_inr, uom, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        line_id,
                        new_order_id,
                        vl["product_id"],
                        vl["requested_qty"],
                        vl["unit_price_inr"],
                        vl["uom"],
                        now,
                        now,
                    ),
                )

            # Auto-enqueue into order_processing_queue if requested
            queue_pos = None
            queue_uuid = None
            if payload.auto_enqueue:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(queue_position), 0) + 1
                    FROM order_processing_queue
                    WHERE status = 'QUEUED';
                    """
                )
                queue_pos = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO order_processing_queue (
                        order_id, queue_position, status, enqueued_at, origin, metadata
                    )
                    VALUES (%s, %s, 'QUEUED', %s, 'MANUAL', %s)
                    RETURNING queue_id;
                    """,
                    (
                        new_order_id,
                        queue_pos,
                        now,
                        json.dumps({"created_by": current_user.user_id, "role": current_user.role.value}),
                    ),
                )
                queue_uuid = str(cur.fetchone()[0])

                # Also insert into dedicated FIFO queue table (Migration 014)
                first_line = validated_lines[0] if validated_lines else {"product_id": "PRD-HRC", "requested_qty": 50.0}
                cur.execute(
                    """
                    INSERT INTO orders_queued (
                        queue_id, order_id, customer_name, product_code, quantity_tons, priority, queue_position, scenario_type
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, %s, %s, 'NORMAL'
                    ) ON CONFLICT (order_id) DO NOTHING;
                    """,
                    (
                        new_order_id,
                        cust_ref,
                        first_line["product_id"],
                        first_line["requested_qty"],
                        norm_priority,
                        queue_pos,
                    ),
                )

            # Append audit event into event_log
            evt_id = str(uuid.uuid4())
            audit_payload = {
                "order_id": new_order_id,
                "customer_ref": cust_ref,
                "entity_id": ent_id,
                "priority": norm_priority,
                "line_count": len(validated_lines),
                "auto_enqueue": payload.auto_enqueue,
                "queue_position": queue_pos,
                "actor_id": current_user.user_id,
            }
            payload_hash = hashlib.sha256(json.dumps(audit_payload, sort_keys=True).encode()).hexdigest()

            cur.execute(
                """
                INSERT INTO event_log (
                    event_id, event_type, entity_type, entity_id,
                    actor_type, actor_id, status, payload_hash, event_timestamp
                )
                VALUES (%s, 'ORDER_CREATED', 'ORDER', %s, 'OPERATOR', %s, 'RECORDED', %s, %s);
                """,
                (evt_id, new_order_id, current_user.user_id, payload_hash, now),
            )

            # Commit the transaction
            conn.commit()

            # Retrieve created order for response
            created_order = _fetch_order_by_id(cur, new_order_id)
            if not created_order:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve created order after commit.",
                )

            logger.info(
                "Order %s successfully created by %s (Queue pos: %s)",
                new_order_id,
                current_user.user_id,
                queue_pos,
            )

            return OrderCreateResponse(
                status="created",
                order_id=new_order_id,
                queue_position=queue_pos,
                queue_id=queue_uuid,
                enqueued=payload.auto_enqueue,
                order=created_order,
            )

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to create order: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failed during order creation: {str(exc)}",
        ) from exc


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
    actor_id = payload.get("actor_id", current_user.user_id)
    return transition_order_status(conn, order_id, new_status, reason=reason, actor_id=actor_id)


# ---------------------------------------------------------------------------
# Order Lifecycle & Blockchain Mining Endpoints
# ---------------------------------------------------------------------------

@router.get("/lifecycle/queued")
def get_lifecycle_queued(
    limit: int = Query(100, ge=1, le=500),
    conn=Depends(get_db),
):
    """Retrieve list of orders pending in the dedicated FIFO queue."""
    from app.services.lifecycle_queue_service import OrderLifecycleService
    return OrderLifecycleService.get_queued_orders(conn, limit=limit)


@router.get("/lifecycle/running")
def get_lifecycle_running(
    conn=Depends(get_db),
):
    """Retrieve list of orders currently running with live agent states."""
    from app.services.lifecycle_queue_service import OrderLifecycleService
    return OrderLifecycleService.get_running_orders(conn)


@router.get("/lifecycle/done")
def get_lifecycle_done(
    limit: int = Query(100, ge=1, le=500),
    conn=Depends(get_db),
):
    """Retrieve completed/processed order history (archival records)."""
    from app.services.lifecycle_queue_service import OrderLifecycleService
    return OrderLifecycleService.get_done_orders(conn, limit=limit)


@router.get("/lifecycle/decisions")
def get_lifecycle_decisions(
    order_id: Optional[str] = Query(None, description="Optional filter by order_id"),
    limit: int = Query(50, ge=1, le=200),
    conn=Depends(get_db),
):
    """Retrieve agent decision logs across specialist agents."""
    from app.services.lifecycle_queue_service import OrderLifecycleService
    return OrderLifecycleService.get_agent_decision_logs(conn, order_id=order_id, limit=limit)


@router.get("/lifecycle/blockchain/blocks")
def get_lifecycle_blockchain_blocks(
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_db),
):
    """Retrieve mined blockchain blocks containing decision transactions."""
    from app.services.lifecycle_queue_service import OrderLifecycleService
    return OrderLifecycleService.get_blockchain_blocks(conn, limit=limit)


@router.post("/lifecycle/run-next")
def run_next_lifecycle_order(
    scenario: str = Query("NORMAL", description="Scenario: NORMAL, SUPPLIER_UNAVAILABLE, BUDGET_BREACH, DELIVERY_DELAY, STOCK_SHORTFALL"),
    conn=Depends(get_db),
):
    """Atomically pop the next FIFO order from the queue, run agent mesh,
    record agent decisions, mine a blockchain block, and archive to orders_done.
    """
    from app.services.lifecycle_queue_service import OrderLifecycleService
    return OrderLifecycleService.pop_and_execute_order(conn, scenario_type=scenario)


@router.post("/lifecycle/run-order/{order_id}")
def run_specific_lifecycle_order(
    order_id: str,
    scenario: str = Query("NORMAL", description="Scenario: NORMAL, SUPPLIER_UNAVAILABLE, BUDGET_BREACH, DELIVERY_DELAY, STOCK_SHORTFALL"),
    conn=Depends(get_db),
):
    """Run a specific order through the agent mesh lifecycle."""
    from app.services.lifecycle_queue_service import OrderLifecycleService
    return OrderLifecycleService.pop_and_execute_order(conn, target_order_id=order_id, scenario_type=scenario)
