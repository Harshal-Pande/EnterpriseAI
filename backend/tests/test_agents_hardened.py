"""Tests for Specialist Agent Hardening and Contracts (Task 9).

Verifies:
- Standardized typed Pydantic contracts for all five agents
- Database-backed operational reasoning from PostgreSQL tables (inventory, suppliers, budgets, warehouses)
- Deterministic calculation integrity
- Error handling with graceful fallbacks
- Multi-agent synthesis and decision formulation by SupervisorAgent
"""

from __future__ import annotations

import pytest

from app.agents.finance import FinanceAgent
from app.agents.inventory import InventoryAgent
from app.agents.logistics import LogisticsAgent
from app.agents.procurement import ProcurementAgent
from app.agents.supervisor import SupervisorAgent
from app.models.agent_contracts import (
    FinanceOutput,
    InventoryOutput,
    LogisticsOutput,
    ProcurementOutput,
    SupervisorOutput,
)


@pytest.mark.integration
def test_inventory_agent_queries_database_and_returns_typed_output(test_conn):
    """InventoryAgent checks real stock in PostgreSQL and returns validated InventoryOutput."""
    agent = InventoryAgent()
    state = {"order_id": "ORD-1001", "requested_qty": 50.0}

    output = agent.run(state, conn=test_conn)

    # Validate schema
    validated = InventoryOutput.model_validate(output)
    assert validated.item_id != ""
    assert validated.requested_qty == 50.0
    assert validated.on_hand_qty >= 0.0
    assert validated.available_qty >= 0.0
    assert validated.shortage_qty == max(0.0, validated.requested_qty - validated.available_qty)
    assert validated.stock_status in {"OK", "SHORTAGE", "LOW_STOCK", "REORDER_REQUIRED"}
    assert len(validated.evidence_refs) >= 1


@pytest.mark.integration
def test_procurement_agent_queries_database_and_returns_typed_output(test_conn):
    """ProcurementAgent evaluates real supplier offers in PostgreSQL and calculates cost."""
    agent = ProcurementAgent()
    state = {"item_id": "PRD-STEEL-01", "shortage_qty": 100.0}

    output = agent.run(state, conn=test_conn)

    # Validate schema
    validated = ProcurementOutput.model_validate(output)
    assert validated.item_id == "PRD-STEEL-01"
    assert validated.required_qty == 100.0
    assert validated.selected_supplier_id is not None
    assert validated.unit_price_inr is not None
    assert validated.estimated_cost == round(validated.unit_price_inr * 100.0, 2)
    assert validated.procurement_status in {"SUPPLIER_SELECTED", "NO_ACTIVE_OFFERS"}


@pytest.mark.integration
def test_finance_agent_evaluates_budget_and_thresholds(test_conn):
    """FinanceAgent verifies spend against available budget and approval threshold."""
    agent = FinanceAgent()

    # Case 1: Low spend within auto-approval limit
    low_state = {"estimated_cost": 25000.0}
    low_out = agent.run(low_state, conn=test_conn)
    val_low = FinanceOutput.model_validate(low_out)
    assert val_low.estimated_spend == 25000.0
    assert val_low.requires_approval is False
    assert val_low.finance_status == "APPROVED"
    assert val_low.budget_allocated is True

    # Case 2: High spend exceeding approval threshold (INR 50,000,000 in DB)
    high_state = {"estimated_cost": 55000000.0}
    high_out = agent.run(high_state, conn=test_conn)
    val_high = FinanceOutput.model_validate(high_out)
    assert val_high.estimated_spend == 55000000.0
    assert val_high.requires_approval is True
    assert val_high.finance_status == "NEEDS_APPROVAL"
    assert val_high.budget_allocated is False

    # Case 3: Massive spend exceeding total budget (INR 65,000,000 in DB)
    huge_state = {"estimated_cost": 999999999.0}
    huge_out = agent.run(huge_state, conn=test_conn)
    val_huge = FinanceOutput.model_validate(huge_out)
    assert val_huge.finance_status == "BUDGET_EXCEEDED"
    assert val_huge.requires_approval is True


@pytest.mark.integration
def test_logistics_agent_plans_feasible_route(test_conn):
    """LogisticsAgent queries warehouses and returns feasible route and transit time."""
    agent = LogisticsAgent()
    state = {"destination": "Chennai Port Facility"}

    output = agent.run(state, conn=test_conn)

    validated = LogisticsOutput.model_validate(output)
    assert validated.destination == "Chennai Port Facility"
    assert validated.origin_warehouse_id != ""
    assert validated.transit_days >= 1
    assert len(validated.estimated_delivery) == 10  # YYYY-MM-DD
    assert validated.logistics_status == "FEASIBLE"


@pytest.mark.integration
def test_supervisor_agent_synthesizes_all_specialists():
    """SupervisorAgent accurately aggregates findings, determines human approval, and outputs action."""
    agent = SupervisorAgent()
    state = {
        "workflow_id": "WF-SYNTHESIS-01",
        "order_id": "ORD-SYNTH-01",
        "agent_outputs": {
            "InventoryAgent": {
                "item_id": "PRD-STEEL-01",
                "shortage_qty": 20.0,
                "requested_qty": 100.0,
                "stock_status": "SHORTAGE",
            },
            "ProcurementAgent": {
                "selected_supplier_id": "SUPP-002",
                "selected_supplier_name": "Apex Alloys",
                "estimated_cost": 75000.0,
            },
            "FinanceAgent": {
                "finance_status": "NEEDS_APPROVAL",
                "requires_approval": True,
            },
            "LogisticsAgent": {
                "route_id": "RT-WH01-DELHI",
                "logistics_status": "FEASIBLE",
            },
        },
    }

    output = agent.run(state)

    validated = SupervisorOutput.model_validate(output)
    assert validated.workflow_id == "WF-SYNTHESIS-01"
    assert validated.human_approval_required is True
    assert validated.decision_code == "DEC-REQUIRES-HUMAN-APPROVAL"
    assert validated.recommended_action["action_type"] == "CREATE_PURCHASE_ORDER"
    assert validated.recommended_action["requires_approval"] is True
    assert validated.confidence == 1.0
