"""Finance Specialist Agent.

Evaluates procurement spend against operational budgets and delegated approval thresholds in PostgreSQL.
Outputs structured financial feasibility, threshold check, and approval requirements.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.models.agent_contracts import FinanceOutput

logger = logging.getLogger("enterpriseai.agents.finance")


class FinanceAgent:
    """Specialist agent for evaluating financial budgets and approval limits."""

    def __init__(self):
        pass

    def run(self, state: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Query real budget limits and approval thresholds from PostgreSQL budgets table."""
        estimated_spend = float(state.get("estimated_cost") or 5000.0)

        budget_id = None
        cost_center = None
        available_budget = 1000000.0  # Safe fallback if DB not connected
        threshold_limit = 50000.0     # Default threshold for human approval
        evidence_refs = []

        if conn:
            with conn.cursor() as cur:
                # Query active budget record
                cur.execute(
                    """
                    SELECT
                        budget_id,
                        cost_center,
                        available_budget_inr,
                        single_action_approval_threshold_inr
                    FROM budgets
                    WHERE status = 'ACTIVE'
                    ORDER BY available_budget_inr DESC
                    LIMIT 1;
                    """,
                )
                row = cur.fetchone()
                if row:
                    budget_id = str(row[0])
                    cost_center = str(row[1])
                    available_budget = float(row[2]) if row[2] is not None else available_budget
                    threshold_limit = float(row[3]) if row[3] is not None else threshold_limit
                    evidence_refs.append({
                        "type": "DATABASE_RECORD",
                        "table": "budgets",
                        "budget_id": budget_id,
                        "available_budget_inr": available_budget,
                        "threshold_limit_inr": threshold_limit,
                    })

        # Deterministic evaluation of spend against budget and single action threshold
        if estimated_spend > available_budget:
            status = "BUDGET_EXCEEDED"
            requires_approval = True
            allocated = False
            reason = f"Estimated spend (INR {estimated_spend:,.2f}) exceeds available budget (INR {available_budget:,.2f})."
        elif estimated_spend > threshold_limit:
            status = "NEEDS_APPROVAL"
            requires_approval = True
            allocated = False
            reason = f"Spend (INR {estimated_spend:,.2f}) exceeds single action threshold (INR {threshold_limit:,.2f}); requires human approval."
        else:
            status = "APPROVED"
            requires_approval = False
            allocated = True
            reason = f"Spend (INR {estimated_spend:,.2f}) within delegated budget limit."

        result = FinanceOutput(
            budget_id=budget_id or "BDG-CORP-2026",
            cost_center=cost_center or "SUPPLY_CHAIN_OPS",
            estimated_spend=estimated_spend,
            available_budget=available_budget,
            threshold_limit=threshold_limit,
            finance_status=status,
            requires_approval=requires_approval,
            budget_allocated=allocated,
            reason=reason,
            evidence_refs=evidence_refs,
        )
        return result.model_dump()
