from typing import Any, Dict, List, Optional, TypedDict


class WorkflowState(TypedDict, total=False):
    """Defines the state structure for the workflow orchestration graph."""

    workflow_id: str
    scenario_id: Optional[str]
    order_id: str
    current_agent: str
    status: str
    inventory_status: Optional[str]
    selected_supplier: Optional[str]
    estimated_cost: Optional[float]
    finance_status: Optional[str]
    route_id: Optional[str]
    audit_trail: List[str]
    agent_outputs: Dict[str, Any]
    error: Optional[str]
