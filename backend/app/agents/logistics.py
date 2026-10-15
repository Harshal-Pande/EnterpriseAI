"""Logistics Specialist Agent.

Evaluates operational warehouses, routes, and shipments in PostgreSQL.
Outputs route feasibility, estimated delivery dates, and carrier metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.models.agent_contracts import LogisticsOutput

logger = logging.getLogger("enterpriseai.agents.logistics")


class LogisticsAgent:
    """Specialist agent for route planning, transit times, and logistics feasibility."""

    def __init__(self):
        pass

    def run(self, state: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Query real warehouses from PostgreSQL and plan feasible route."""
        from app.services.data_tools import get_freight_lanes

        destination = state.get("destination") or "Pune Plant 1"
        origin_wh = state.get("warehouse_id")
        agent_run_id = state.get("agent_run_id")
        scenario_id = state.get("scenario_id")

        transit_days = 3
        carrier_score = 0.95
        evidence_refs = []

        if conn:
            lane_res = get_freight_lanes(
                conn,
                origin_warehouse_id=origin_wh,
                destination=destination,
                agent_run_id=agent_run_id,
                scenario_id=scenario_id,
            )
            origin_wh = lane_res["origin_warehouse_id"]
            transit_days = lane_res["transit_days"]
            carrier_score = lane_res["carrier_score"]
            evidence_refs.extend(lane_res["evidence_refs"])

        now = datetime.now(timezone.utc)
        estimated_delivery = (now + timedelta(days=transit_days)).strftime("%Y-%m-%d")
        route_id = f"RT-{origin_wh or 'WH-01'}-TO-{destination[:4].upper()}"

        result = LogisticsOutput(
            route_id=route_id,
            origin_warehouse_id=origin_wh or "WH-01",
            destination=destination,
            transit_days=transit_days,
            estimated_delivery=estimated_delivery,
            logistics_status="FEASIBLE",
            carrier_score=carrier_score,
            evidence_refs=evidence_refs,
        )
        return result.model_dump()
