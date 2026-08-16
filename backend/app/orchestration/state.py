from typing import TypedDict, Optional, List, Any

class WorkflowState(TypedDict):
    """
    Defines the state structure for the LangGraph workflow.
    """
    workflow_id: str
    order_id: str
    current_agent: str
    next_agent: str
    status: str
    
    # Order specifics
    item_name: str
    required_quantity: int
    
    # Inventory
    inventory_status: Optional[str]
    available_quantity: Optional[int]
    shortage: Optional[int]
    
    # Procurement
    supplier_candidates: Optional[List[dict[str, Any]]]
    selected_supplier: Optional[str]
    estimated_cost: Optional[float]
    
    # Finance
    budget: Optional[float]
    finance_status: Optional[str]
    
    # Logistics
    route_id: Optional[str]
    route_feasibility: Optional[str]
    
    # Audit
    audit_trail: List[str]
