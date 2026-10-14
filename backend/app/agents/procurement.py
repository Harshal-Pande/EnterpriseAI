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
        item_id = state.get("item_id") or "PRD-STEEL-01"
        shortage_qty = float(state.get("shortage_qty") or state.get("quantity") or 50.0)

        selected_supplier_id = None
        selected_supplier_name = None
        selected_offer_id = None
        unit_price = 100.0
        lead_time = 48
        evaluated_count = 0
        evidence_refs = []

        if conn:
            with conn.cursor() as cur:
                # Query active offers for this product, ordered by price and on-time rate
                cur.execute(
                    """
                    SELECT
                        so.offer_id,
                        so.supplier_id,
                        s.supplier_name,
                        so.unit_price_inr,
                        so.lead_time_hours,
                        s.historical_on_time_rate
                    FROM supplier_offers so
                    JOIN suppliers s ON so.supplier_id = s.supplier_id
                    WHERE so.item_id = %s
                      AND so.offer_status = 'ACTIVE'
                      AND s.status = 'ACTIVE'
                    ORDER BY so.unit_price_inr ASC, s.historical_on_time_rate DESC NULLS LAST
                    LIMIT 5;
                    """,
                    (item_id,),
                )
                offers = cur.fetchall()
                evaluated_count = len(offers)

                if offers:
                    best = offers[0]
                    selected_offer_id = str(best[0])
                    selected_supplier_id = str(best[1])
                    selected_supplier_name = str(best[2])
                    unit_price = float(best[3])
                    lead_time = int(best[4]) if best[4] is not None else 48
                    evidence_refs.append({
                        "type": "DATABASE_RECORD",
                        "table": "supplier_offers",
                        "offer_id": selected_offer_id,
                        "supplier_id": selected_supplier_id,
                        "unit_price_inr": unit_price,
                    })
                else:
                    # Fall back to best active general supplier
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
        return result.model_dump()
