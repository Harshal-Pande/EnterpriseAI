from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db import database

router = APIRouter()


@router.get("/health")
def health_check():
    """Liveness probe. Reports whether the application process is running.

    Remains independent of database state so process liveness is not coupled
    to database availability.
    """
    return {"status": "healthy", "service": "Enterprise AI Mesh API"}


@router.get("/ready")
@router.get("/health/ready")
def readiness_check():
    """Readiness probe. Verifies database connectivity by executing SELECT 1.

    Returns HTTP 200 when PostgreSQL is reachable and ready to serve traffic.
    Returns HTTP 503 Service Unavailable when the database is unreachable or down,
    without exposing credentials or internal errors.
    """
    is_ready, db_status = database.check_db_readiness()
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": db_status},
        )
    return {"status": "ready", "database": db_status}
