from fastapi import FastAPI
from app.api import health, orders, workflow, agents, audit

app = FastAPI(
    title="Enterprise AI Mesh Backend",
    description="Backend API for the Enterprise AI Mesh platform. Currently a starter implementation.",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])

@app.get("/")
def read_root():
    return {"message": "Enterprise AI Mesh API is running."}
