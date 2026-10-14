"""Supervisor Agent.

Synthesizes findings from specialist agents (Inventory, Procurement, Finance, Logistics).
Constructs recommended actions, evaluates approval requirements, and optionally records decisions.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from app.models.agent_contracts import SupervisorOutput

logger = logging.getLogger("enterpriseai.agents.supervisor")


class SupervisorAgent:
    """Orchestrator and synthesis specialist for the Enterprise AI multi-agent mesh."""

    def __init__(self):
        pass

    def run(self, state: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Synthesize specialist findings, evaluate human approval gating, and formulate decision."""
        workflow_id = state.get("workflow_id", "WF-UNKNOWN")
        order_id = state.get("order_id", "ORD-UNKNOWN")
        scenario_id = state.get("scenario_id") or workflow_id

        # Inspect specialist findings
        agent_outputs = state.get("agent_outputs", {})
        inv_data = agent_outputs.get("InventoryAgent", {})
        proc_data = agent_outputs.get("ProcurementAgent", {})
        fin_data = agent_outputs.get("FinanceAgent", {})
        log_data = agent_outputs.get("LogisticsAgent", {})

        # Determine human approval requirements
        human_approval_required = False
        decision_code = "DEC-AUTO-APPROVED"
        approval_status = "NOT_REQUIRED"

        if fin_data.get("requires_approval") or fin_data.get("finance_status") == "NEEDS_APPROVAL":
            human_approval_required = True
            decision_code = "DEC-REQUIRES-HUMAN-APPROVAL"
            approval_status = "PENDING"
        elif fin_data.get("finance_status") == "BUDGET_EXCEEDED":
            human_approval_required = True
            decision_code = "DEC-BLOCKED-BUDGET-EXCEEDED"
            approval_status = "PENDING"

        # Formulate recommended action
        recommended_action = {
            "action_type": "CREATE_PURCHASE_ORDER" if inv_data.get("shortage_qty", 0) > 0 else "FULFILL_ORDER",
            "item_id": inv_data.get("item_id", "PRD-STEEL-01"),
            "quantity": inv_data.get("shortage_qty") or inv_data.get("requested_qty", 100),
            "supplier_id": proc_data.get("selected_supplier_id", "SUPP-001"),
            "estimated_cost": proc_data.get("estimated_cost", 5000.0),
            "route_id": log_data.get("route_id", "RT-WH01-PUNE"),
            "requires_approval": human_approval_required,
        }

        summary = (
            f"Supervisor synthesized multi-agent analysis for order {order_id}. "
            f"Inventory shortage: {inv_data.get('shortage_qty', 0)}. "
            f"Procurement supplier: {proc_data.get('selected_supplier_name', 'Default')}. "
            f"Finance check: {fin_data.get('finance_status', 'APPROVED')}. "
            f"Human approval required: {human_approval_required}."
        )

        specialists = list(agent_outputs.keys())
        if "SupervisorAgent" not in specialists:
            specialists.insert(0, "SupervisorAgent")

        evidence_refs = [
            {"agent": "InventoryAgent", "status": inv_data.get("stock_status")},
            {"agent": "ProcurementAgent", "supplier": proc_data.get("selected_supplier_id")},
            {"agent": "FinanceAgent", "status": fin_data.get("finance_status")},
            {"agent": "LogisticsAgent", "status": log_data.get("logistics_status")},
        ]

        # If connected to DB and valid UUID scenario exists, record in decisions table
        if conn and scenario_id:
            try:
                val_uuid = uuid.UUID(scenario_id)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO decisions (
                            decision_id, scenario_id, workflow_run_id, decision_at,
                            supervisor_summary, decision_code, recommended_action,
                            policy_checks, human_approval_required, approval_status,
                            evidence_refs
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            str(uuid.uuid4()),
                            str(val_uuid),
                            str(val_uuid),
                            datetime.now(timezone.utc),
                            summary,
                            decision_code,
                            json.dumps(recommended_action),
                            json.dumps([]),
                            human_approval_required,
                            approval_status,
                            json.dumps(evidence_refs),
                        ),
                    )
                    conn.commit()
            except Exception as exc:
                logger.warning("Could not persist decision record: %s", exc)

        result = SupervisorOutput(
            workflow_id=workflow_id,
            order_id=order_id,
            current_agent="SupervisorAgent",
            status="DECISION_SYNTHESIZED",
            decision_code=decision_code,
            summary=summary,
            human_approval_required=human_approval_required,
            recommended_action=recommended_action,
            specialists_invoked=specialists,
            confidence=1.0,
            evidence_refs=evidence_refs,
        )
        return result.model_dump()
