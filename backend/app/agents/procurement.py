"""
Procurement Agent
Purpose: Identifies suppliers for missing stock and negotiates/selects based on criteria.
"""
from app.orchestration.state import WorkflowState

class ProcurementAgent:
    def __init__(self):
        pass

    def __call__(self, state: WorkflowState) -> dict:
        print(f"[Procurement] Sourcing shortage for order: {state.get('order_id')}")
        
        shortage = state.get("shortage", 0)
        
        # Mock supplier evaluation
        candidates = [
            {"id": "SUP-A", "price": 6400, "availability": 0},
            {"id": "SUP-B", "price": 6600, "availability": 150},
            {"id": "SUP-C", "price": 7400, "availability": 200},
        ]
        
        # Pick the cheapest one with enough availability
        valid_candidates = [c for c in candidates if c["availability"] >= shortage]
        if valid_candidates:
            selected = min(valid_candidates, key=lambda x: x["price"])
            selected_supplier = selected["id"]
            estimated_cost = selected["price"] * shortage
        else:
            selected_supplier = "NONE"
            estimated_cost = 0.0
            
        audit_trail = state.get("audit_trail", [])
        audit_trail.append(f"Procurement selected {selected_supplier} for {shortage} units at cost {estimated_cost}")
        
        from app.db.neo4j_db import track_decision
        try:
            track_decision("procurement", "Supplier Selection", state.get("order_id"), f"selected={selected_supplier}")
        except Exception as e:
            print(f"Neo4j tracking failed: {e}")
            
        return {
            "current_agent": "procurement",
            "supplier_candidates": candidates,
            "selected_supplier": selected_supplier,
            "estimated_cost": estimated_cost,
            "audit_trail": audit_trail
        }
