"""
Finance Agent
Purpose: Reviews procurement costs and approves/denies based on budget rules.
Input/State: Receives cost estimates from Procurement Agent.
"""

from app.orchestration.state import WorkflowState

class FinanceAgent:
    def __init__(self):
        pass

    def __call__(self, state: WorkflowState) -> dict:
        print(f"[Finance] Validating budget for order: {state.get('order_id')}")
        
        estimated_cost = state.get("estimated_cost", 0.0)
        budget = state.get("budget", 850000.0)  # Default mock budget if not provided
        
        if estimated_cost <= budget:
            status = "APPROVED"
        else:
            status = "REJECTED_BUDGET_EXCEEDED"
            
        audit_trail = state.get("audit_trail", [])
        audit_trail.append(f"Finance validation: cost={estimated_cost}, budget={budget}, status={status}")
        
        from app.db.neo4j_db import track_decision
        try:
            track_decision("finance", "Financial Approval", state.get("order_id"), f"status={status}")
        except Exception as e:
            print(f"Neo4j tracking failed: {e}")
            
        return {
            "current_agent": "finance",
            "finance_status": status,
            "budget": budget,
            "audit_trail": audit_trail,
            "budget_allocated": True
        }
