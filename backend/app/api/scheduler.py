"""Scheduler management API endpoints.

Provides:
- GET /api/scheduler/status : Read-only scheduler state and cycle history
- POST /api/scheduler/trigger : On-demand execution of an eligible scenario cycle
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from app.db.database import get_db
from app.services.scheduler_service import default_scheduler

logger = logging.getLogger("enterpriseai.api.scheduler")

router = APIRouter()


@router.get("/status")
def get_scheduler_status(conn=Depends(get_db)) -> Dict[str, Any]:
    """Retrieve observable status, lease locking state, and last outcome of the scenario scheduler."""
    return default_scheduler.get_status(conn)


@router.post("/trigger", status_code=status.HTTP_200_OK)
def trigger_scheduler_cycle(conn=Depends(get_db)) -> Dict[str, Any]:
    """Manually trigger a scheduler cycle to execute the next eligible scenario."""
    return default_scheduler.run_cycle(conn, force=True)
