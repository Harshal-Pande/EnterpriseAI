import os
from sentence_transformers import SentenceTransformer
from app.db.database import SessionLocal
from app.db.models import SupplierContext

docs = [
    {
        "supplier_id": "SUP-A",
        "context_text": "Supplier A (Apex Industrial) is reliable but has a high lead time. They specialize in bulk orders and cheap materials. Their warehouse is located in Ohio. Use for large quantity standard parts."
    },
    {
        "supplier_id": "SUP-B",
        "context_text": "Supplier B (Bharat Heavy) provides fast shipping and excellent quality control for industrial pumps and heavy machinery. Located in Texas. Good for urgent, high-value components."
    },
    {
        "supplier_id": "SUP-C",
        "context_text": "Supplier C (Crestline Global) is a premium supplier but expensive. Use them only for emergency shortages or when other suppliers are out of stock. They can deliver anywhere in 24 hours."
    }
]

def seed_database():
    db = SessionLocal()
    
    # Check if already seeded
    existing = db.query(SupplierContext).count()
    if existing > 0:
        print("Database already seeded with SupplierContext.")
        db.close()
        return

    print("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print("Embedding documents and seeding database...")
    for doc in docs:
        embedding = model.encode(doc["context_text"])
        
        supplier_context = SupplierContext(
            supplier_id=doc["supplier_id"],
            context_text=doc["context_text"],
            embedding=embedding
        )
        db.add(supplier_context)
    
    db.commit()
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_database()
