from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import get_db
from app.models.inventory import InventoryItem, InventorySummary

logger = logging.getLogger("enterpriseai.inventory")

router = APIRouter()

ALLOWED_STOCK_SIGNALS = {"NORMAL", "LOW_STOCK", "CRITICAL", "OUT_OF_STOCK", "EXCESS"}
ALLOWED_SORT_FIELDS = {
    "inventory_id": "inv.inventory_id",
    "product_name": "p.product_name",
    "item_id": "inv.item_id",
    "warehouse_id": "inv.warehouse_id",
    "on_hand_qty": "inv.on_hand_qty",
    "available_qty": "inv.available_qty",
    "stock_signal": "inv.stock_signal",
}


@router.get("/summary", response_model=InventorySummary)
def get_inventory_summary(conn=Depends(get_db)):
    """Retrieve aggregate telemetry and health metrics across all inventory."""
    sql = """
        SELECT
            COUNT(DISTINCT inv.inventory_id) AS total_skus,
            COALESCE(SUM(inv.on_hand_qty), 0) AS total_on_hand_qty,
            COALESCE(SUM(inv.available_qty), 0) AS total_available_qty,
            COALESCE(SUM(inv.reserved_qty), 0) AS total_reserved_qty,
            COUNT(*) FILTER (WHERE inv.stock_signal = 'NORMAL') AS normal_count,
            COUNT(*) FILTER (WHERE inv.stock_signal = 'LOW_STOCK') AS low_stock_count,
            COUNT(*) FILTER (WHERE inv.stock_signal = 'CRITICAL') AS critical_count,
            COUNT(*) FILTER (WHERE inv.stock_signal = 'OUT_OF_STOCK') AS out_of_stock_count
        FROM inventory inv;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            r = cur.fetchone()
    except Exception as exc:
        logger.error("Database query failed in get_inventory_summary: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving inventory summary",
        ) from exc

    return InventorySummary(
        total_skus=int(r[0]) if r and r[0] is not None else 0,
        total_on_hand_qty=float(r[1]) if r and r[1] is not None else 0.0,
        total_available_qty=float(r[2]) if r and r[2] is not None else 0.0,
        total_reserved_qty=float(r[3]) if r and r[3] is not None else 0.0,
        normal_count=int(r[4]) if r and r[4] is not None else 0,
        low_stock_count=int(r[5]) if r and r[5] is not None else 0,
        critical_count=int(r[6]) if r and r[6] is not None else 0,
        out_of_stock_count=int(r[7]) if r and r[7] is not None else 0,
    )


@router.get("/", response_model=List[InventoryItem])
def list_inventory(
    warehouse_id: Optional[str] = Query(None, description="Filter by warehouse ID"),
    item_id: Optional[str] = Query(None, alias="product_id", description="Filter by item/product ID"),
    stock_signal: Optional[str] = Query(None, alias="status", description="Filter by stock signal / status"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query("inventory_id", description="Sort field"),
    sort_order: str = Query("asc", description="Sort direction (asc or desc)"),
    conn=Depends(get_db),
):
    """Retrieve inventory balances and telemetry joined with product and warehouse data."""
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

    if warehouse_id:
        clauses.append("inv.warehouse_id = %s")
        params.append(warehouse_id)

    if item_id:
        clauses.append("inv.item_id = %s")
        params.append(item_id)

    if stock_signal:
        norm_signal = stock_signal.upper().replace(" ", "_")
        if norm_signal not in ALLOWED_STOCK_SIGNALS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stock signal: {stock_signal}. Allowed values: {sorted(ALLOWED_STOCK_SIGNALS)}",
            )
        clauses.append("inv.stock_signal = %s")
        params.append(norm_signal)

    if category:
        clauses.append("p.product_category ILIKE %s")
        params.append(f"%{category}%")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_column = ALLOWED_SORT_FIELDS[sort_by_lower]

    sql = f"""
        SELECT
            inv.inventory_id,
            inv.item_id,
            p.product_name,
            p.product_category,
            inv.warehouse_id,
            w.warehouse_name,
            w.warehouse_type,
            inv.on_hand_qty,
            inv.reserved_qty,
            inv.available_qty,
            inv.uom,
            inv.stock_signal,
            rp.reorder_point_qty,
            rp.safety_stock_qty,
            rp.target_stock_qty,
            inv.as_of_timestamp
        FROM inventory inv
        JOIN products p ON inv.item_id = p.product_id
        JOIN warehouses w ON inv.warehouse_id = w.warehouse_id
        LEFT JOIN reorder_policies rp ON inv.item_id = rp.item_id AND inv.warehouse_id = rp.warehouse_id
        {where_sql}
        ORDER BY {order_column} {sort_order_upper}, inv.inventory_id {sort_order_upper}
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("Database query failed in list_inventory: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving inventory items",
        ) from exc

    items: list[InventoryItem] = []
    for r in rows:
        on_hand = float(r[7]) if r[7] is not None else 0.0
        available = float(r[9]) if r[9] is not None else 0.0
        reorder_point = float(r[12]) if r[12] is not None else None
        shortage = max(0.0, reorder_point - available) if reorder_point is not None and available < reorder_point else 0.0

        items.append(
            InventoryItem(
                id=r[0],
                inventory_id=r[0],
                name=r[2],
                product_name=r[2],
                item_id=r[1],
                product_id=r[1],
                product_category=r[3],
                warehouse_id=r[4],
                warehouse_name=r[5],
                warehouse_type=r[6],
                quantity=on_hand,
                on_hand_qty=on_hand,
                reserved_qty=float(r[8]) if r[8] is not None else 0.0,
                available_qty=available,
                uom=r[10],
                stock_signal=r[11],
                status=r[11],
                reorder_threshold=reorder_point,
                reorder_point_qty=reorder_point,
                safety_stock_qty=float(r[13]) if r[13] is not None else None,
                target_stock_qty=float(r[14]) if r[14] is not None else None,
                shortage=shortage,
                as_of_timestamp=r[15].isoformat() if r[15] else None,
            )
        )
    return items


@router.get("/{inventory_id}", response_model=InventoryItem)
def get_inventory_item(inventory_id: str, conn=Depends(get_db)):
    """Retrieve detailed telemetry for a single inventory record by ID."""
    sql = """
        SELECT
            inv.inventory_id,
            inv.item_id,
            p.product_name,
            p.product_category,
            inv.warehouse_id,
            w.warehouse_name,
            w.warehouse_type,
            inv.on_hand_qty,
            inv.reserved_qty,
            inv.available_qty,
            inv.uom,
            inv.stock_signal,
            rp.reorder_point_qty,
            rp.safety_stock_qty,
            rp.target_stock_qty,
            inv.as_of_timestamp
        FROM inventory inv
        JOIN products p ON inv.item_id = p.product_id
        JOIN warehouses w ON inv.warehouse_id = w.warehouse_id
        LEFT JOIN reorder_policies rp ON inv.item_id = rp.item_id AND inv.warehouse_id = rp.warehouse_id
        WHERE inv.inventory_id = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (inventory_id,))
            r = cur.fetchone()
            if not r:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Inventory item {inventory_id} not found",
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database query failed in get_inventory_item: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving inventory item",
        ) from exc

    on_hand = float(r[7]) if r[7] is not None else 0.0
    available = float(r[9]) if r[9] is not None else 0.0
    reorder_point = float(r[12]) if r[12] is not None else None
    shortage = max(0.0, reorder_point - available) if reorder_point is not None and available < reorder_point else 0.0

    return InventoryItem(
        id=r[0],
        inventory_id=r[0],
        name=r[2],
        product_name=r[2],
        item_id=r[1],
        product_id=r[1],
        product_category=r[3],
        warehouse_id=r[4],
        warehouse_name=r[5],
        warehouse_type=r[6],
        quantity=on_hand,
        on_hand_qty=on_hand,
        reserved_qty=float(r[8]) if r[8] is not None else 0.0,
        available_qty=available,
        uom=r[10],
        stock_signal=r[11],
        status=r[11],
        reorder_threshold=reorder_point,
        reorder_point_qty=reorder_point,
        safety_stock_qty=float(r[13]) if r[13] is not None else None,
        target_stock_qty=float(r[14]) if r[14] is not None else None,
        shortage=shortage,
        as_of_timestamp=r[15].isoformat() if r[15] else None,
    )
