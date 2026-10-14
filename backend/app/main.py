import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    actions,
    agents,
    approvals,
    audit,
    health,
    inventory,
    orchestration,
    orders,
    policies,
    scheduler,
    suppliers,
    workflow,
)
from app.core.security import UserRole, require_role
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

# Configure CORS for frontend access
cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS")
if cors_origins_env:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

viewer_auth = [Depends(require_role(UserRole.VIEWER))]

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"], dependencies=viewer_auth)
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"], dependencies=viewer_auth)
app.include_router(suppliers.router, prefix="/api/suppliers", tags=["suppliers"], dependencies=viewer_auth)
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"], dependencies=viewer_auth)
app.include_router(agents.router, prefix="/api/agents", tags=["agents"], dependencies=viewer_auth)
app.include_router(audit.router, prefix="/api/audit", tags=["audit"], dependencies=viewer_auth)
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["scheduler"], dependencies=viewer_auth)
app.include_router(policies.router, prefix="/api/policies", tags=["policies"], dependencies=viewer_auth)
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"], dependencies=viewer_auth)
app.include_router(actions.router, prefix="/api/actions", tags=["actions"], dependencies=viewer_auth)
app.include_router(
    orchestration.router,
    prefix="/api/orchestration",
    tags=["orchestration"],
    dependencies=[Depends(require_role(UserRole.VIEWER))],
)


@app.get("/")
def read_root():
    return {"message": "Enterprise AI Mesh API is running."}
