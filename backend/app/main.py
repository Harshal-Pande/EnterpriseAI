from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import agents, audit, health, inventory, orders, suppliers, workflow
from app.db.database import close_db_pool, init_db_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connection pool if configured (does not block startup if DB is down)
    init_db_pool()
    yield
    # Cleanly close all connections in pool on application shutdown
    close_db_pool()


app = FastAPI(
    title="Enterprise AI Mesh Backend",
    description="Backend API for the Enterprise AI Mesh platform. Currently a starter implementation.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(suppliers.router, prefix="/api/suppliers", tags=["suppliers"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])


@app.get("/")
def read_root():
    return {"message": "Enterprise AI Mesh API is running."}
