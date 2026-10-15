"""Internal Data Tools Layer for Specialist Agents (Task P5.1).

Provides parameterized, safe database queries for specialist agents.
Specialist agents invoke these tools rather than issuing ad-hoc SQL queries.
Automatically logs every tool call into `agent_tool_calls` and persists
structured evidence references into `evidence_references` (Migration 009).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("enterpriseai.data_tools")


def _record_tool_call_and_evidence(
    conn,
    tool_name: str,
    input_params: Dict[str, Any],
    output_data: Dict[str, Any],
    data_refs: List[Dict[str, Any]],
    execution_ms: int,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Optional[str]:
    """Helper to record tool call execution and associated evidence references."""
    if not conn:
        return None

    tool_call_id = str(uuid.uuid4())
    try:
        with conn.cursor() as cur:
            # Check if agent_run_id is valid UUID and exists in agent_runs
            valid_agent_run_uuid = None
            if agent_run_id:
                try:
                    cand_uuid = uuid.UUID(str(agent_run_id))
                    cur.execute("SELECT 1 FROM agent_runs WHERE agent_run_id = %s;", (str(cand_uuid),))
                    if cur.fetchone():
                        valid_agent_run_uuid = str(cand_uuid)
                except (ValueError, Exception):
                    valid_agent_run_uuid = None

            # Check scenario_id
            valid_scenario_uuid = None
            if scenario_id:
                try:
                    s_uuid = uuid.UUID(str(scenario_id))
                    cur.execute("SELECT 1 FROM scenario_instances WHERE scenario_id = %s;", (str(s_uuid),))
                    if cur.fetchone():
                        valid_scenario_uuid = str(s_uuid)
                except (ValueError, Exception):
                    valid_scenario_uuid = None

            if valid_agent_run_uuid:
                cur.execute(
                    """
                    INSERT INTO agent_tool_calls (
                        tool_call_id, agent_run_id, scenario_id, tool_name, tool_version,
                        input_params, output_data, data_refs, execution_ms, status
                    )
                    VALUES (%s, %s, %s, %s, 'v1', %s, %s, %s, %s, 'COMPLETED');
                    """,
                    (
                        tool_call_id,
                        valid_agent_run_uuid,
                        valid_scenario_uuid,
                        tool_name,
                        json.dumps(input_params),
                        json.dumps(output_data),
                        json.dumps(data_refs),
                        execution_ms,
                    ),
                )

                # Insert evidence references
                for ref in data_refs:
                    ev_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO evidence_references (
                            evidence_id, agent_run_id, tool_call_id, scenario_id,
                            source_table, source_pk, snapshot_data, evidence_type, citation_label
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'DATA_QUERY', %s);
                        """,
                        (
                            ev_id,
                            valid_agent_run_uuid,
                            tool_call_id,
                            valid_scenario_uuid,
                            ref.get("table", "unknown"),
                            str(ref.get("pk", "unknown")),
                            json.dumps(ref.get("data", {})),
                            ref.get("citation_label", f"{ref.get('table')}:{ref.get('pk')}"),
                        ),
                    )
                conn.commit()
                return tool_call_id
    except Exception as e:
        logger.warning(f"Failed to record tool call {tool_name} to database: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    return None


def get_inventory_snapshot(
    conn,
    item_id: str,
    warehouse_id: Optional[str] = None,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch on-hand, reserved, and net available inventory for an item."""
    start_time = time.perf_counter()
    input_params = {"item_id": item_id, "warehouse_id": warehouse_id}
    data_refs: List[Dict[str, Any]] = []

    on_hand = 0.0
    reserved = 0.0
    available = 0.0
    reorder_point = None
    safety_stock = None
    records = []

    if conn:
        with conn.cursor() as cur:
            if warehouse_id:
                cur.execute(
                    """
                    SELECT inventory_id, item_id, warehouse_id, on_hand_qty, reserved_qty, available_qty, stock_signal
                    FROM inventory
                    WHERE item_id = %s AND warehouse_id = %s;
                    """,
                    (item_id, warehouse_id),
                )
            else:
                cur.execute(
                    """
                    SELECT inventory_id, item_id, warehouse_id, on_hand_qty, reserved_qty, available_qty, stock_signal
                    FROM inventory
                    WHERE item_id = %s;
                    """,
                    (item_id,),
                )
            rows = cur.fetchall()
            for r in rows:
                inv_id, itm, wh, oh, res, av, sig = r[0], r[1], r[2], float(r[3]), float(r[4]), float(r[5]), r[6]
                on_hand += oh
                reserved += res
                available += av
                rec = {
                    "inventory_id": inv_id,
                    "item_id": itm,
                    "warehouse_id": wh,
                    "on_hand_qty": oh,
                    "reserved_qty": res,
                    "available_qty": av,
                    "stock_signal": sig,
                }
                records.append(rec)
                data_refs.append({
                    "ref": f"inventory:{inv_id}",
                    "table": "inventory",
                    "pk": inv_id,
                    "citation_label": f"Inventory {itm} @ {wh}",
                    "data": rec,
                })

            # Check reorder policy
            cur.execute(
                """
                SELECT policy_id, reorder_point_qty, safety_stock_qty, target_stock_qty
                FROM reorder_policies
                WHERE item_id = %s
                LIMIT 1;
                """,
                (item_id,),
            )
            rp = cur.fetchone()
            if rp:
                reorder_point = float(rp[1])
                safety_stock = float(rp[2])
                data_refs.append({
                    "ref": f"reorder_policies:{rp[0]}",
                    "table": "reorder_policies",
                    "pk": rp[0],
                    "citation_label": f"Reorder Policy for {item_id}",
                    "data": {"reorder_point_qty": reorder_point, "safety_stock_qty": safety_stock},
                })

    exec_ms = int((time.perf_counter() - start_time) * 1000)
    output_data = {
        "item_id": item_id,
        "warehouse_id": warehouse_id,
        "on_hand_qty": on_hand,
        "reserved_qty": reserved,
        "available_qty": available,
        "reorder_point_qty": reorder_point,
        "safety_stock_qty": safety_stock,
        "warehouses_count": len(records),
        "records": records,
        "evidence_refs": data_refs,
    }

    _record_tool_call_and_evidence(
        conn,
        "get_inventory_snapshot",
        input_params,
        output_data,
        data_refs,
        exec_ms,
        agent_run_id,
        scenario_id,
    )
    return output_data


def get_stock_coverage(
    conn,
    item_id: str,
    daily_burn_rate: Optional[float] = None,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate days of inventory cover based on available stock and consumption rate."""
    start_time = time.perf_counter()
    input_params = {"item_id": item_id, "daily_burn_rate": daily_burn_rate}
    inv = get_inventory_snapshot(conn, item_id)
    available_qty = inv["available_qty"]

    burn = daily_burn_rate if (daily_burn_rate and daily_burn_rate > 0) else 10.0
    days_of_cover = round(available_qty / burn, 1)

    exec_ms = int((time.perf_counter() - start_time) * 1000)
    output_data = {
        "item_id": item_id,
        "available_qty": available_qty,
        "daily_burn_rate": burn,
        "days_of_cover": days_of_cover,
        "is_critical": days_of_cover < 3.0,
        "evidence_refs": inv["evidence_refs"],
    }

    _record_tool_call_and_evidence(
        conn,
        "get_stock_coverage",
        input_params,
        output_data,
        inv["evidence_refs"],
        exec_ms,
        agent_run_id,
        scenario_id,
    )
    return output_data


def get_order_details(
    conn,
    order_id: str,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch order header and associated order lines."""
    start_time = time.perf_counter()
    input_params = {"order_id": order_id}
    data_refs: List[Dict[str, Any]] = []

    order_info: Dict[str, Any] = {}
    lines: List[Dict[str, Any]] = []

    if conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT order_id, customer_ref, status, priority, required_delivery_at, customer_id
                FROM orders
                WHERE order_id = %s OR customer_ref = %s
                LIMIT 1;
                """,
                (order_id, order_id),
            )
            o = cur.fetchone()
            if o:
                order_info = {
                    "order_id": o[0],
                    "customer_ref": o[1],
                    "status": o[2],
                    "priority": o[3],
                    "required_delivery_at": str(o[4]) if o[4] else None,
                    "customer_id": o[5],
                }
                data_refs.append({
                    "ref": f"orders:{o[0]}",
                    "table": "orders",
                    "pk": o[0],
                    "citation_label": f"Order {o[0]} (Ref: {o[1]})",
                    "data": order_info,
                })

                cur.execute(
                    """
                    SELECT order_line_id, product_id, requested_qty, unit_price_inr, uom
                    FROM order_lines
                    WHERE order_id = %s;
                    """,
                    (o[0],),
                )
                for l in cur.fetchall():
                    l_dict = {
                        "order_line_id": l[0],
                        "product_id": l[1],
                        "requested_qty": float(l[2]),
                        "unit_price_inr": float(l[3]) if l[3] is not None else 0.0,
                        "uom": l[4],
                    }
                    lines.append(l_dict)
                    data_refs.append({
                        "ref": f"order_lines:{l[0]}",
                        "table": "order_lines",
                        "pk": l[0],
                        "citation_label": f"Order line {l[1]} ({l[2]} {l[4]})",
                        "data": l_dict,
                    })

    exec_ms = int((time.perf_counter() - start_time) * 1000)
    output_data = {
        "order": order_info,
        "lines": lines,
        "total_lines": len(lines),
        "evidence_refs": data_refs,
    }

    _record_tool_call_and_evidence(
        conn,
        "get_order_details",
        input_params,
        output_data,
        data_refs,
        exec_ms,
        agent_run_id,
        scenario_id,
    )
    return output_data


def get_supplier_offers(
    conn,
    item_id: str,
    required_qty: float = 0.0,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve active supplier offers ranked by unit price and supplier reliability."""
    start_time = time.perf_counter()
    input_params = {"item_id": item_id, "required_qty": required_qty}
    data_refs: List[Dict[str, Any]] = []
    ranked_offers: List[Dict[str, Any]] = []

    if conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    so.offer_id,
                    so.supplier_id,
                    s.supplier_name,
                    so.unit_price_inr,
                    so.lead_time_hours,
                    s.historical_on_time_rate,
                    so.max_available_qty,
                    s.risk_band
                FROM supplier_offers so
                JOIN suppliers s ON so.supplier_id = s.supplier_id
                WHERE so.item_id = %s
                  AND so.offer_status = 'ACTIVE'
                  AND s.status = 'ACTIVE'
                ORDER BY so.unit_price_inr ASC, s.historical_on_time_rate DESC NULLS LAST;
                """,
                (item_id,),
            )
            for row in cur.fetchall():
                offer_dict = {
                    "offer_id": str(row[0]),
                    "supplier_id": str(row[1]),
                    "supplier_name": str(row[2]),
                    "unit_price_inr": float(row[3]),
                    "lead_time_hours": int(row[4]) if row[4] is not None else 48,
                    "historical_on_time_rate": float(row[5]) if row[5] is not None else 0.9,
                    "max_available_qty": float(row[6]) if row[6] is not None else 1000.0,
                    "risk_band": str(row[7]) if row[7] is not None else "LOW",
                }
                ranked_offers.append(offer_dict)
                data_refs.append({
                    "ref": f"supplier_offers:{offer_dict['offer_id']}",
                    "table": "supplier_offers",
                    "pk": offer_dict["offer_id"],
                    "citation_label": f"Offer {offer_dict['supplier_name']} (INR {offer_dict['unit_price_inr']})",
                    "data": offer_dict,
                })

    exec_ms = int((time.perf_counter() - start_time) * 1000)
    best_offer = ranked_offers[0] if ranked_offers else None
    output_data = {
        "item_id": item_id,
        "required_qty": required_qty,
        "offers_count": len(ranked_offers),
        "best_offer": best_offer,
        "ranked_offers": ranked_offers,
        "is_single_source": len(ranked_offers) == 1,
        "evidence_refs": data_refs,
    }

    _record_tool_call_and_evidence(
        conn,
        "get_supplier_offers",
        input_params,
        output_data,
        data_refs,
        exec_ms,
        agent_run_id,
        scenario_id,
    )
    return output_data


def get_bom_requirements(
    conn,
    product_id: str,
    required_qty: float,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate multi-tier raw material component requirements for a finished good."""
    start_time = time.perf_counter()
    input_params = {"product_id": product_id, "required_qty": required_qty}
    data_refs: List[Dict[str, Any]] = []
    components: List[Dict[str, Any]] = []

    if conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT bom_line_id, input_item_id, quantity_per_output_unit, consumption_uom
                FROM bill_of_materials
                WHERE output_product_id = %s;
                """,
                (product_id,),
            )
            for row in cur.fetchall():
                bom_id = row[0]
                comp_id = row[1]
                qty_per_unit = float(row[2])
                gross_qty = round(required_qty * qty_per_unit, 3)

                comp_dict = {
                    "bom_line_id": bom_id,
                    "input_item_id": comp_id,
                    "quantity_per_output_unit": qty_per_unit,
                    "consumption_uom": row[3],
                    "required_component_qty": gross_qty,
                }
                components.append(comp_dict)
                data_refs.append({
                    "ref": f"bill_of_materials:{bom_id}",
                    "table": "bill_of_materials",
                    "pk": bom_id,
                    "citation_label": f"BOM requirement {comp_id} for {product_id}",
                    "data": comp_dict,
                })

    exec_ms = int((time.perf_counter() - start_time) * 1000)
    output_data = {
        "product_id": product_id,
        "required_qty": required_qty,
        "components_count": len(components),
        "components": components,
        "evidence_refs": data_refs,
    }

    _record_tool_call_and_evidence(
        conn,
        "get_bom_requirements",
        input_params,
        output_data,
        data_refs,
        exec_ms,
        agent_run_id,
        scenario_id,
    )
    return output_data


def check_budget_headroom(
    conn,
    cost_center: Optional[str] = None,
    proposed_spend: float = 0.0,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify operational budget availability and delegated single-action threshold."""
    start_time = time.perf_counter()
    input_params = {"cost_center": cost_center, "proposed_spend": proposed_spend}
    data_refs: List[Dict[str, Any]] = []

    budget_id = None
    available_budget = 1000000.0
    committed_spend = 0.0
    threshold = 50000.0
    cc = cost_center or "SUPPLY_CHAIN_OPS"

    if conn:
        with conn.cursor() as cur:
            if cost_center:
                cur.execute(
                    """
                    SELECT budget_id, cost_center, available_budget_inr, committed_spend_inr, single_action_approval_threshold_inr
                    FROM budgets
                    WHERE cost_center = %s AND status = 'ACTIVE'
                    LIMIT 1;
                    """,
                    (cost_center,),
                )
            else:
                cur.execute(
                    """
                    SELECT budget_id, cost_center, available_budget_inr, committed_spend_inr, single_action_approval_threshold_inr
                    FROM budgets
                    WHERE status = 'ACTIVE'
                    ORDER BY available_budget_inr DESC
                    LIMIT 1;
                    """
                )
            row = cur.fetchone()
            if row:
                budget_id = str(row[0])
                cc = str(row[1])
                available_budget = float(row[2]) if row[2] is not None else available_budget
                committed_spend = float(row[3]) if row[3] is not None else 0.0
                threshold = float(row[4]) if row[4] is not None else threshold

                data_refs.append({
                    "ref": f"budgets:{budget_id}",
                    "table": "budgets",
                    "pk": budget_id,
                    "citation_label": f"Budget {cc} (Avail: INR {available_budget:,.2f})",
                    "data": {
                        "budget_id": budget_id,
                        "cost_center": cc,
                        "available_budget_inr": available_budget,
                        "threshold_limit_inr": threshold,
                    },
                })

    exceeds_budget = proposed_spend > available_budget
    exceeds_threshold = proposed_spend > threshold
    requires_approval = exceeds_budget or exceeds_threshold

    exec_ms = int((time.perf_counter() - start_time) * 1000)
    output_data = {
        "budget_id": budget_id or "BDG-DEFAULT",
        "cost_center": cc,
        "proposed_spend": proposed_spend,
        "available_budget": available_budget,
        "committed_spend": committed_spend,
        "threshold_limit": threshold,
        "exceeds_budget": exceeds_budget,
        "exceeds_threshold": exceeds_threshold,
        "requires_approval": requires_approval,
        "evidence_refs": data_refs,
    }

    _record_tool_call_and_evidence(
        conn,
        "check_budget_headroom",
        input_params,
        output_data,
        data_refs,
        exec_ms,
        agent_run_id,
        scenario_id,
    )
    return output_data


def get_freight_lanes(
    conn,
    origin_warehouse_id: Optional[str] = None,
    destination: Optional[str] = None,
    agent_run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve feasible transit routes, carrier options, and estimated transit days."""
    start_time = time.perf_counter()
    input_params = {"origin_warehouse_id": origin_warehouse_id, "destination": destination}
    data_refs: List[Dict[str, Any]] = []
    lanes: List[Dict[str, Any]] = []

    transit_days = 3
    carrier_score = 0.95
    origin_wh = origin_warehouse_id or "WH-01"
    dest = destination or "Pune Plant 1"

    if conn:
        with conn.cursor() as cur:
            # Check warehouses table using exact columns: location_label
            cur.execute(
                """
                SELECT warehouse_id, warehouse_name, location_label
                FROM warehouses
                WHERE warehouse_id = %s OR warehouse_name = %s
                LIMIT 1;
                """,
                (origin_wh, origin_wh),
            )
            wh = cur.fetchone()
            if wh:
                origin_wh = str(wh[0])
                data_refs.append({
                    "ref": f"warehouses:{wh[0]}",
                    "table": "warehouses",
                    "pk": wh[0],
                    "citation_label": f"Warehouse {wh[1]} ({wh[2]})",
                    "data": {"warehouse_id": wh[0], "name": wh[1], "location_label": wh[2]},
                })

            # Check transport_lanes if available (migration 006)
            try:
                cur.execute(
                    """
                    SELECT tl.lane_id, tl.origin_city, tl.dest_city, tl.mode, tl.transit_days_min, tl.transit_days_max,
                           c.carrier_id, c.carrier_name, c.on_time_rate
                    FROM transport_lanes tl
                    JOIN carriers c ON tl.carrier_id = c.carrier_id
                    WHERE tl.status = 'ACTIVE'
                    LIMIT 5;
                    """
                )
                for r in cur.fetchall():
                    lane_dict = {
                        "lane_id": r[0],
                        "origin_city": r[1],
                        "dest_city": r[2],
                        "mode": r[3],
                        "transit_days_min": r[4],
                        "transit_days_max": r[5],
                        "carrier_id": r[6],
                        "carrier_name": r[7],
                        "on_time_rate": float(r[8]) if r[8] is not None else 0.95,
                    }
                    lanes.append(lane_dict)
                    data_refs.append({
                        "ref": f"transport_lanes:{r[0]}",
                        "table": "transport_lanes",
                        "pk": r[0],
                        "citation_label": f"Lane {r[1]} -> {r[2]} via {r[7]} ({r[3]})",
                        "data": lane_dict,
                    })
                if lanes:
                    transit_days = lanes[0]["transit_days_min"]
                    carrier_score = lanes[0]["on_time_rate"]
            except Exception:
                pass

    exec_ms = int((time.perf_counter() - start_time) * 1000)
    route_id = f"RT-{origin_wh}-TO-{dest[:4].upper()}"
    output_data = {
        "route_id": route_id,
        "origin_warehouse_id": origin_wh,
        "destination": dest,
        "transit_days": transit_days,
        "carrier_score": carrier_score,
        "lanes": lanes,
        "evidence_refs": data_refs,
    }

    _record_tool_call_and_evidence(
        conn,
        "get_freight_lanes",
        input_params,
        output_data,
        data_refs,
        exec_ms,
        agent_run_id,
        scenario_id,
    )
    return output_data
