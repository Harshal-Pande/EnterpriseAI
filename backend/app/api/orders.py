from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Order, WorkflowState as DBWorkflowState
from pydantic import BaseModel
from app.orchestration.graph import WorkflowGraph

router = APIRouter()

# Instantiate graph once
workflow_graph = WorkflowGraph()

class OrderCreate(BaseModel):
    customer_id: str
    item_name: str
    quantity: int
    budget: float = 850000.0

@router.get("/")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    # Map them to the shape the frontend expects (or close to it)
    result = []
    for o in orders:
        ws = db.query(DBWorkflowState).filter(DBWorkflowState.order_id == o.id).first()
        current_agent = ws.current_agent if ws else "supervisor"
        result.append({
            "id": o.id,
            "customer": o.customer_id,
            "product": ws.state_data.get("item_name", "Unknown") if ws else "Unknown",
            "quantity": ws.state_data.get("required_quantity", 0) if ws else 0,
            "budget": ws.state_data.get("budget", 0.0) if ws else 0.0,
            "status": o.status,
            "currentAgent": current_agent,
            "createdAt": o.created_at.isoformat()
        })
    return result

@router.post("/")
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    new_order = Order(
        customer_id=order_data.customer_id,
        status="processing"
    )
    db.add(new_order)
    db.flush() # To get new_order.id
    
    # Initialize LangGraph state
    initial_state = {
        "workflow_id": "", # Will be set after DB insert or we can generate UUID early
        "order_id": new_order.id,
        "current_agent": "supervisor",
        "status": "active",
        "item_name": order_data.item_name,
        "required_quantity": order_data.quantity,
        "budget": order_data.budget,
        "audit_trail": []
    }
    
    # Track order in Neo4j
    from app.db.neo4j_db import get_neo4j
    neo4j_db = get_neo4j()
    try:
        query = """
        MATCH (c:Customer {id: $customer_id})
        // Fallback to finding product by name or ID
        MATCH (p:Product) WHERE p.id = $item_name OR p.name CONTAINS $item_name
        CREATE (o:Order {id: $order_id, quantity: $quantity, budget: $budget})
        CREATE (c)-[:PLACED]->(o)
        CREATE (o)-[:REQUIRES]->(p)
        """
        neo4j_db.execute_query(query, {
            "customer_id": order_data.customer_id,
            "item_name": order_data.item_name,
            "order_id": new_order.id,
            "quantity": order_data.quantity,
            "budget": order_data.budget
        })
    except Exception as e:
        print(f"Failed to track order in Neo4j: {e}")
        
    # Run the workflow synchronously
    final_state = workflow_graph.run_workflow(initial_state)
    
    # Update order status if completed
    if final_state.get("status") == "completed":
        new_order.status = "Completed"
    
    new_workflow = DBWorkflowState(
        order_id=new_order.id,
        status=final_state.get("status", "active"),
        current_agent=final_state.get("current_agent", "supervisor"),
        state_data=final_state
    )
    db.add(new_workflow)
    
    db.commit()
    db.refresh(new_workflow)
    
    return {"status": "created", "order_id": new_order.id, "workflow_id": new_workflow.id, "final_state": final_state}
