from langgraph.graph import StateGraph, END
from app.orchestration.state import WorkflowState
from app.agents.supervisor import SupervisorAgent
from app.agents.inventory import InventoryAgent
from app.agents.procurement import ProcurementAgent
from app.agents.finance import FinanceAgent
from app.agents.logistics import LogisticsAgent

class WorkflowGraph:
    def __init__(self):
        # Initialize the state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes for each agent
        workflow.add_node("supervisor", SupervisorAgent())
        workflow.add_node("inventory", InventoryAgent())
        workflow.add_node("procurement", ProcurementAgent())
        workflow.add_node("finance", FinanceAgent())
        workflow.add_node("logistics", LogisticsAgent())
        
        # Define the conditional routing logic from the supervisor
        def supervisor_router(state: WorkflowState) -> str:
            return state.get("next_agent", "END")
            
        workflow.add_conditional_edges(
            "supervisor",
            supervisor_router,
            {
                "inventory": "inventory",
                "procurement": "procurement",
                "finance": "finance",
                "logistics": "logistics",
                "END": END
            }
        )
        
        # Define paths back to the supervisor
        workflow.add_edge("inventory", "supervisor")
        workflow.add_edge("procurement", "supervisor")
        workflow.add_edge("finance", "supervisor")
        workflow.add_edge("logistics", "supervisor")
        
        # Set the entry point
        workflow.set_entry_point("supervisor")
        
        self.app = workflow.compile()

    def run_workflow(self, initial_state: dict):
        """
        Invokes the compiled LangGraph workflow.
        """
        print(f"Starting LangGraph workflow for order {initial_state.get('order_id')}")
        
        # Ensure audit trail exists
        if "audit_trail" not in initial_state or initial_state["audit_trail"] is None:
            initial_state["audit_trail"] = []
            
        final_state = self.app.invoke(initial_state)
        
        # Return updated state
        final_state["status"] = "completed" if final_state.get("next_agent") == "END" else final_state.get("status", "in_progress")
        return final_state
