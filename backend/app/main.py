import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger("enterpriseai.main")


try:
    from backend.db.connection import load_project_env
except ImportError:
    try:
        from db.connection import load_project_env
    except ImportError:
        _bdir = Path(__file__).resolve().parent.parent
        if str(_bdir) not in sys.path:
            sys.path.insert(0, str(_bdir))
        from db.connection import load_project_env
load_project_env()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    actions,
    agents,
    approvals,
    audit,
    graph,
    health,
    inventory,
    orchestration,
    orders,
    policies,
    scheduler,
    suppliers,
    system,
    tasks,
    workflow,
    ws,
)
from app.core.config import validate_startup_config
from app.core.events import default_event_manager
from app.core.security import UserRole, require_role
from app.db.database import close_db_pool, init_db_pool
from app.services.scheduler_service import default_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate environment credentials and refuse startup if defaults are used in production
    validate_startup_config()
    # Initialize connection pool if configured (does not block startup if DB is down)
    init_db_pool()
    default_event_manager.set_loop(asyncio.get_running_loop())
    default_scheduler.start()
    # Start in-process task worker if explicitly enabled (Phase P4)
    if os.environ.get("ENABLE_TASK_WORKER", "false").lower() in ("true", "1"):
        try:
            from app.worker import start_default_worker
            start_default_worker()
        except Exception as _worker_err:
            logger.warning("Task worker failed to start: %s", _worker_err)
    yield
    default_scheduler.stop()
    # Stop task worker if running
    try:
        from app.worker import stop_default_worker
        stop_default_worker()
    except Exception:
        pass
    # Cleanly close all connections in pool on application shutdown
    close_db_pool()


app = FastAPI(
    title="Enterprise AI Mesh Backend",
    description="Backend API for the Enterprise AI Mesh platform.",
    version="0.2.0",
    lifespan=lifespan,
)

import uuid
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Configure CORS for frontend access
cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS") or os.environ.get("CORS_ORIGINS")
if cors_origins_env:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

allow_wildcard = "*" in allowed_origins
if allow_wildcard:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )



@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", f"corr-{uuid.uuid4().hex[:8]}")
    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": msg,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": msg,
                "details": exc.detail if not isinstance(exc.detail, str) else None,
                "correlation_id": correlation_id,
            },
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    correlation_id = getattr(request.state, "correlation_id", f"corr-{uuid.uuid4().hex[:8]}")
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "detail": errors,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request parameter or body validation failed",
                "details": errors,
                "correlation_id": correlation_id,
            },
        },
    )


viewer_auth = [Depends(require_role(UserRole.VIEWER))]

# Routers mounted under both /api and /api/v1 for 100% contract compatibility
routers = [
    (health.router, "", ["health"], []),
    (orders.router, "/orders", ["orders"], viewer_auth),
    (inventory.router, "/inventory", ["inventory"], viewer_auth),
    (suppliers.router, "/suppliers", ["suppliers"], viewer_auth),
    (workflow.router, "/workflow", ["workflow"], viewer_auth),
    (agents.router, "/agents", ["agents"], viewer_auth),
    (audit.router, "/audit", ["audit"], viewer_auth),
    (graph.router, "/graph", ["graph"], viewer_auth),
    (scheduler.router, "/scheduler", ["scheduler"], viewer_auth),
    (policies.router, "/policies", ["policies"], viewer_auth),
    (approvals.router, "/approvals", ["approvals"], viewer_auth),
    (actions.router, "/actions", ["actions"], viewer_auth),
    (orchestration.router, "/orchestration", ["orchestration"], viewer_auth),
    (tasks.router, "/tasks", ["tasks"], viewer_auth),
    (system.router, "", ["system"], viewer_auth),
    (ws.router, "", ["websocket"], []),
]

for router_obj, subprefix, tags, deps in routers:
    # Mount primary /api
    app.include_router(router_obj, prefix=f"/api{subprefix}", tags=tags, dependencies=deps)
    # Mount alias /api/v1
    app.include_router(router_obj, prefix=f"/api/v1{subprefix}", tags=[f"v1-{t}" for t in tags], dependencies=deps)


@app.get("/")
def read_root():
    return {
        "service": "Enterprise AI Mesh API",
        "version": "0.2.0",
        "status": "healthy",
        "endpoints": ["/api", "/api/v1", "/api/health", "/api/health/ready", "/docs"],
    }
