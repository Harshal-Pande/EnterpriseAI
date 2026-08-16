from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import WorkflowState

router = APIRouter()

@router.get("/{workflow_id}")
def get_workflow_status(workflow_id: str, db: Session = Depends(get_db)):
    workflow = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "workflow_id": workflow.id,
        "order_id": workflow.order_id,
        "status": workflow.status,
        "current_agent": workflow.current_agent,
        "state_data": workflow.state_data
    }
