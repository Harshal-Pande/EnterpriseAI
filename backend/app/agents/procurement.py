"""Procurement Specialist Agent.

Evaluates operational suppliers, supplier_offers, and contracts in PostgreSQL.
Selects optimal active supplier based on price, reliability score, and lead times.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.models.agent_contracts import ProcurementOutput

logger = logging.getLogger("enterpriseai.agents.procurement")


class ProcurementAgent:
    """Specialist agent for evaluating suppliers and negotiating procurement options."""

    def __init__(self):
        pass

    def run(self, state: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Query real supplier offers from PostgreSQL and select best active candidate."""
        from app.services.data_tools import get_supplier_offers

        item_id = state.get("item_id") or "PRD-STEEL-01"
        shortage_qty = float(state.get("shortage_qty") or state.get("quantity") or 50.0)
        agent_run_id = state.get("agent_run_id")
        scenario_id = state.get("scenario_id")

        selected_supplier_id = None
        selected_supplier_name = None
        selected_offer_id = None
        unit_price = 100.0
        lead_time = 48
        evaluated_count = 0
        evidence_refs = []
        is_single_source = False

        if conn:
            offers_res = get_supplier_offers(
                conn,
                item_id=item_id,
                required_qty=shortage_qty,
                agent_run_id=agent_run_id,
                scenario_id=scenario_id,
            )
            evaluated_count = offers_res["offers_count"]
            is_single_source = offers_res["is_single_source"]
            evidence_refs.extend(offers_res["evidence_refs"])

            best = offers_res.get("best_offer")
            if best:
                selected_offer_id = best["offer_id"]
                selected_supplier_id = best["supplier_id"]
                selected_supplier_name = best["supplier_name"]
                unit_price = best["unit_price_inr"]
                lead_time = best["lead_time_hours"]
            else:
                # Fall back to best active general supplier
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT supplier_id, supplier_name, historical_on_time_rate
                        FROM suppliers
                        WHERE status = 'ACTIVE'
                        ORDER BY historical_on_time_rate DESC NULLS LAST
                        LIMIT 1;
                        """,
                    )
                    supp = cur.fetchone()
                    if supp:
                        selected_supplier_id = str(supp[0])
                        selected_supplier_name = str(supp[1])
                        evaluated_count = 1
                        evidence_refs.append({
                            "type": "DATABASE_RECORD",
                            "table": "suppliers",
                            "supplier_id": selected_supplier_id,
                        })

        estimated_cost = round(unit_price * shortage_qty, 2)
        proc_status = "SUPPLIER_SELECTED" if selected_supplier_id else "NO_ACTIVE_OFFERS"

        result = ProcurementOutput(
            item_id=item_id,
            required_qty=shortage_qty,
            selected_supplier_id=selected_supplier_id or "SUPP-001",
            selected_supplier_name=selected_supplier_name or "Precision Castings Ltd",
            selected_offer_id=selected_offer_id,
            unit_price_inr=unit_price,
            estimated_cost=estimated_cost,
            lead_time_hours=lead_time,
            suppliers_evaluated_count=evaluated_count,
            procurement_status=proc_status,
            evidence_refs=evidence_refs,
        )
        out_dict = result.model_dump()
        out_dict["is_single_source"] = is_single_source
        return out_dict
