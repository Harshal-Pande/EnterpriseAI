from app.orchestration.state import WorkflowState

class InventoryAgent:
    def __init__(self):
        pass

    def __call__(self, state: WorkflowState) -> dict:
        print(f"[Inventory] Checking stock for order: {state.get('order_id')}")
        
        required = state.get("required_quantity", 0)
        # Mock available quantity for now
        available = 42 
        shortage = max(0, required - available)
        
        status = "REORDER_REQUIRED" if shortage > 0 else "OK"
        
        audit_trail = state.get("audit_trail", [])
        audit_trail.append(f"Inventory check: required={required}, available={available}, shortage={shortage}")
        
        from app.db.neo4j_db import track_decision
        try:
            track_decision("inventory", "Inventory Check", state.get("order_id"), f"shortage={shortage}")
        except Exception as e:
            print(f"Neo4j tracking failed: {e}")
            
        return {
            "current_agent": "inventory",
            "inventory_status": status,
            "available_quantity": available,
            "shortage": shortage,
            "audit_trail": audit_trail
        }
