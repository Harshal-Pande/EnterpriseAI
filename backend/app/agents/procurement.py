"""
Procurement Agent
Purpose: Identifies suppliers for missing stock and negotiates/selects based on criteria (now using RAG context).
"""
from app.orchestration.state import WorkflowState
from app.db.database import SessionLocal
from app.db.models import SupplierContext
from sentence_transformers import SentenceTransformer

class ProcurementAgent:
    def __init__(self):
        # Load embedding model once
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def __call__(self, state: WorkflowState) -> dict:
        order_id = state.get("order_id")
        print(f"[Procurement] Sourcing shortage for order: {order_id}")
        
        shortage = state.get("shortage", 0)
        
        # We need something to query about. The state doesn't have an explicit 'item_name',
        # but in a real scenario we would extract it. We'll use a generic query or infer from context.
        # For demo purposes, let's pretend the requested item is "industrial pumps" if not specified.
        item_requested = state.get("item_name", "industrial pumps")
        
        # 1. RAG Query: Find best matching supplier policies for the requested item
        query_embedding = self.model.encode(item_requested)
        
        db = SessionLocal()
        try:
            # Get top 2 most relevant supplier contexts via vector search
            relevant_contexts = db.query(SupplierContext).order_by(
                SupplierContext.embedding.l2_distance(query_embedding)
            ).limit(2).all()
            
            rag_info = []
            top_supplier_ids = []
            for ctx in relevant_contexts:
                rag_info.append(f"[{ctx.supplier_id}] {ctx.context_text}")
                top_supplier_ids.append(ctx.supplier_id)
        finally:
            db.close()
            
        print(f"[Procurement] RAG Context retrieved: {rag_info}")

        # 2. Candidate Evaluation
        candidates = [
            {"id": "SUP-A", "price": 6400, "availability": 0},
            {"id": "SUP-B", "price": 6600, "availability": 150},
            {"id": "SUP-C", "price": 7400, "availability": 200},
        ]
        
        # Filter valid candidates (enough availability)
        valid_candidates = [c for c in candidates if c["availability"] >= shortage]
        
        # 3. Decision Logic influenced by RAG
        # If any of the top RAG suppliers are valid, pick the cheapest among THEM.
        # Otherwise, fall back to cheapest overall valid.
        selected_supplier = "NONE"
        estimated_cost = 0.0
        decision_reason = "No valid suppliers."

        if valid_candidates:
            # Intersection of valid candidates and top RAG matches
            rag_valid = [c for c in valid_candidates if c["id"] in top_supplier_ids]
            
            if rag_valid:
                selected = min(rag_valid, key=lambda x: x["price"])
                decision_reason = f"Selected {selected['id']} based on RAG context match and lowest price."
            else:
                selected = min(valid_candidates, key=lambda x: x["price"])
                decision_reason = f"Selected {selected['id']} based on lowest price (RAG preferred suppliers lacked availability)."
                
            selected_supplier = selected["id"]
            estimated_cost = selected["price"] * shortage

        # Audit trail
        audit_trail = state.get("audit_trail", [])
        audit_trail.append(f"Procurement queried RAG for '{item_requested}': found {top_supplier_ids}")
        audit_trail.append(f"Procurement {decision_reason} Cost: {estimated_cost}")
        
        from app.db.neo4j_db import track_decision
        try:
            track_decision("procurement", "Supplier Selection", order_id, f"selected={selected_supplier}, reason={decision_reason}")
        except Exception as e:
            print(f"Neo4j tracking failed: {e}")
            
        return {
            "current_agent": "procurement",
            "supplier_candidates": candidates,
            "selected_supplier": selected_supplier,
            "estimated_cost": estimated_cost,
            "audit_trail": audit_trail
        }
