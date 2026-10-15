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
        from app.services.data_tools import get_bom_requirements, get_inventory_snapshot

        order_id = state.get("order_id", "ORD-1042")
        item_id = state.get("product_id") or state.get("item_id")
        requested_qty = float(state.get("requested_qty") or state.get("quantity") or 100.0)
        warehouse_id = state.get("warehouse_id")
        agent_run_id = state.get("agent_run_id")
        scenario_id = state.get("scenario_id")

        on_hand = 0.0
        reserved = 0.0
        available = 0.0
        reorder_point = None
        safety_stock = None
        evidence_refs = []

        if conn:
            # If item_id not provided in state, fetch from order_lines
            if not item_id and order_id:
                with conn.cursor() as cur:
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
                with conn.cursor() as cur:
                    cur.execute("SELECT item_id, warehouse_id FROM inventory LIMIT 1;")
                    first_inv = cur.fetchone()
                    if first_inv:
                        item_id = first_inv[0]
                        warehouse_id = warehouse_id or first_inv[1]

            if item_id:
                snapshot = get_inventory_snapshot(
                    conn,
                    item_id=item_id,
                    warehouse_id=warehouse_id,
                    agent_run_id=agent_run_id,
                    scenario_id=scenario_id,
                )
                on_hand = snapshot["on_hand_qty"]
                reserved = snapshot["reserved_qty"]
                available = snapshot["available_qty"]
                reorder_point = snapshot["reorder_point_qty"]
                safety_stock = snapshot["safety_stock_qty"]
                evidence_refs.extend(snapshot["evidence_refs"])

        # Calculate shortage deterministically
        effective_item = item_id or "PRD-STEEL-01"
        if state.get("shortage_qty") is not None:
            shortage = float(state.get("shortage_qty"))
        else:
            shortage = max(0.0, requested_qty - available)
        stock_status = "OK" if shortage == 0.0 else "SHORTAGE"
        action_required = "none" if shortage == 0.0 else "procurement"

        # Check BOM component breakdown if finished goods are short
        bom_components = []
        if conn and shortage > 0 and effective_item:
            try:
                bom_res = get_bom_requirements(
                    conn,
                    product_id=effective_item,
                    required_qty=shortage,
                    agent_run_id=agent_run_id,
                    scenario_id=scenario_id,
                )
                bom_components = bom_res.get("components", [])
                evidence_refs.extend(bom_res.get("evidence_refs", []))
            except Exception as e:
                logger.debug(f"BOM lookup skipped: {e}")

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
        out_dict = result.model_dump()
        if bom_components:
            out_dict["bom_components"] = bom_components
        return out_dict
