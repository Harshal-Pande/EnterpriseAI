from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, orders, workflow, agents, audit, demo_data

app = FastAPI(
    title="Enterprise AI Mesh Backend",
    description="Backend API for the Enterprise AI Mesh platform. Currently a starter implementation.",
    version="0.1.0",
)

# Allow CORS for the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(agents.router, prefix="/api/agents_old", tags=["agents"]) # kept for backwards compatibility if needed
app.include_router(audit.router, prefix="/api/audit_old", tags=["audit"]) # kept for backwards compatibility if needed
app.include_router(demo_data.router, prefix="/api", tags=["demo_data"])

from app.db.neo4j_db import get_neo4j, seed_graph

@app.on_event("startup")
def startup_event():
    neo4j_db = get_neo4j()
    try:
        neo4j_db.connect()
        # Create schema constraints if not exist
        schema_query = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (w:Warehouse) REQUIRE w.id IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE;",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE;"
        ]
        for q in schema_query:
            neo4j_db.execute_query(q)
        # Seed graph
        seed_graph()
    except Exception as e:
        print(f"Neo4j connection error during startup: {e}")

@app.on_event("shutdown")
def shutdown_event():
    get_neo4j().close()

@app.get("/")
def read_root():
    return {"message": "Enterprise AI Mesh API is running."}
