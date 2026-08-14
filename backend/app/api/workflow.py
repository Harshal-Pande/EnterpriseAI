from fastapi import APIRouter

router = APIRouter()

@router.get("/{workflow_id}")
def get_workflow_status(workflow_id: str):
    # Starter implementation
    return {"workflow_id": workflow_id, "status": "active", "current_agent": "InventoryAgent"}
