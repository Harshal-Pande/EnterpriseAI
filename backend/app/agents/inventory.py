"""Inventory Specialist Agent.

Evaluates operational stock levels, safety stock, and reorder policies in PostgreSQL.
Outputs structured findings, shortages, and allocation recommendations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.models.agent_contracts import InventoryOutput

logger = logging.getLogger("enterpriseai.agents.inventory")


class InventoryAgent:
    """Specialist agent for inventory stock checks and shortage identification."""

    def __init__(self):
        pass

    def run(self, state: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Check real stock levels from PostgreSQL inventory and reorder_policies."""
        order_id = state.get("order_id", "ORD-1042")
        item_id = state.get("product_id") or state.get("item_id")
        requested_qty = float(state.get("requested_qty") or state.get("quantity") or 100.0)
        warehouse_id = state.get("warehouse_id")

        on_hand = 0.0
        reserved = 0.0
        available = 0.0
        reorder_point = None
        safety_stock = None
        evidence_refs = []

        if conn:
            with conn.cursor() as cur:
                # If item_id not provided in state, fetch from order_lines
                if not item_id and order_id:
                    cur.execute(
                        "SELECT product_id, requested_qty FROM order_lines WHERE order_id = %s LIMIT 1;",
                        (order_id,),
                    )
                    ol = cur.fetchone()
                    if ol:
                        item_id = ol[0]
                        if not (state.get("requested_qty") or state.get("quantity")):
                            requested_qty = float(ol[1])

                # If still not found, get first product from inventory
                if not item_id:
                    cur.execute("SELECT item_id, warehouse_id FROM inventory LIMIT 1;")
                    first_inv = cur.fetchone()
                    if first_inv:
                        item_id = first_inv[0]
                        warehouse_id = warehouse_id or first_inv[1]

                # Query inventory table
                if item_id:
                    if warehouse_id:
                        cur.execute(
                            """
                            SELECT on_hand_qty, reserved_qty, available_qty, stock_signal, inventory_id
                            FROM inventory
                            WHERE item_id = %s AND warehouse_id = %s;
                            """,
                            (item_id, warehouse_id),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT SUM(on_hand_qty), SUM(reserved_qty), SUM(available_qty), 'AGGREGATED', 'ALL'
                            FROM inventory
                            WHERE item_id = %s;
                            """,
                            (item_id,),
                        )
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        on_hand = float(row[0])
                        reserved = float(row[1])
                        available = float(row[2])
                        evidence_refs.append({
                            "type": "DATABASE_RECORD",
                            "table": "inventory",
                            "item_id": item_id,
                            "available_qty": available,
                        })

                    # Query reorder_policies
                    cur.execute(
                        """
                        SELECT reorder_point_qty, safety_stock_qty, target_stock_qty
                        FROM reorder_policies
                        WHERE item_id = %s LIMIT 1;
                        """,
                        (item_id,),
                    )
                    rp = cur.fetchone()
                    if rp:
                        reorder_point = float(rp[0])
                        safety_stock = float(rp[1])
                        evidence_refs.append({
                            "type": "DATABASE_RECORD",
                            "table": "reorder_policies",
                            "reorder_point": reorder_point,
                            "safety_stock": safety_stock,
                        })

        # Calculate shortage deterministically
        effective_item = item_id or "PRD-STEEL-01"
        if state.get("shortage_qty") is not None:
            shortage = float(state.get("shortage_qty"))
        else:
            shortage = max(0.0, requested_qty - available)
        stock_status = "OK" if shortage == 0.0 else "SHORTAGE"
        action_required = "none" if shortage == 0.0 else "procurement"

        result = InventoryOutput(
            item_id=effective_item,
            warehouse_id=warehouse_id,
            on_hand_qty=on_hand,
            reserved_qty=reserved,
            available_qty=available,
            requested_qty=requested_qty,
            shortage_qty=shortage,
            stock_status=stock_status,
            reorder_point_qty=reorder_point,
            safety_stock_qty=safety_stock,
            action_required=action_required,
            evidence_refs=evidence_refs,
        )
        return result.model_dump()
