from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    actions,
    agents,
    approvals,
    audit,
    health,
    inventory,
    orders,
    policies,
    scheduler,
    suppliers,
    workflow,
)
from app.db.database import close_db_pool, init_db_pool
from app.services.scheduler_service import default_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connection pool if configured (does not block startup if DB is down)
    init_db_pool()
    default_scheduler.start()
    yield
    default_scheduler.stop()
    # Cleanly close all connections in pool on application shutdown
    close_db_pool()


app = FastAPI(
    title="Enterprise AI Mesh Backend",
    description="Backend API for the Enterprise AI Mesh platform.",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(suppliers.router, prefix="/api/suppliers", tags=["suppliers"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["scheduler"])
app.include_router(policies.router, prefix="/api/policies", tags=["policies"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])


@app.get("/")
def read_root():
    return {"message": "Enterprise AI Mesh API is running."}
