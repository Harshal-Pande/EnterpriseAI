from typing import TypedDict, Optional, List

class WorkflowState(TypedDict):
    """
    Defines the state structure for the LangGraph workflow.
    """
    workflow_id: str
    order_id: str
    current_agent: str
    status: str
    inventory_status: Optional[str]
    selected_supplier: Optional[str]
    estimated_cost: Optional[float]
    finance_status: Optional[str]
    route_id: Optional[str]
    audit_trail: List[str]
