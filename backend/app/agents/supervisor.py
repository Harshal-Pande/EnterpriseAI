from app.orchestration.state import WorkflowState
import time

class SupervisorAgent:
    def __init__(self):
        pass

    def __call__(self, state: WorkflowState) -> dict:
        """
        Supervisor routing logic.
        Examines state and determines next step.
        """
        print(f"[Supervisor] Evaluating state for order: {state.get('order_id')}")
        
        # Simple routing logic
        if not state.get("inventory_status"):
            next_agent = "inventory"
            status = "Checking Inventory"
        elif not state.get("selected_supplier") and state.get("shortage", 0) > 0:
            next_agent = "procurement"
            status = "Procuring Shortage"
        elif not state.get("finance_status"):
            next_agent = "finance"
            status = "Awaiting Finance Approval"
        elif not state.get("route_feasibility"):
            next_agent = "logistics"
            status = "Scheduling Logistics"
        else:
            next_agent = "END"
            status = "Completed"
            
        audit_trail = state.get("audit_trail", [])
        audit_trail.append(f"Supervisor routed to {next_agent}")
        
        return {
            "current_agent": "supervisor",
            "next_agent": next_agent,
            "status": status,
            "audit_trail": audit_trail
        }
