"""Task Queue API — Phase P4.

Provides batch control and task monitoring endpoints:
- GET  /api/tasks/stats        - Queue statistics by status/type
- GET  /api/tasks/             - List tasks with filtering
- POST /api/tasks/enqueue      - Enqueue a single task
- GET  /api/tasks/{task_id}    - Get task details
- POST /api/tasks/{task_id}/cancel - Cancel a pending task
- POST /api/tasks/batches/generate - Generate 1,000-task backlog (demo/test)
- GET  /api/tasks/batches/     - List batches
- GET  /api/tasks/worker/status - Worker process status
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.security import AuthUser, UserRole, require_role
from app.db.database import get_db
from app.worker import (
    cancel_task,
    enqueue_task,
    generate_1000_task_backlog,
    get_default_worker,
    get_queue_stats,
)

logger = logging.getLogger("enterpriseai.api.tasks")
router = APIRouter()

VALID_TASK_TYPES = {
    "ORCHESTRATION", "SCENARIO_RUN", "AGENT_RUN", "DATA_SYNC",
    "BLOCKCHAIN_ANCHOR", "NOTIFICATION", "CLEANUP", "BATCH_LOAD", "HEALTH_CHECK",
}


class EnqueueRequest(BaseModel):
    task_type: str = Field(..., description="Task type (must be registered)")
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    priority: int = Field(5, ge=1, le=10)
    scenario_id: Optional[str] = None
    max_attempts: int = Field(3, ge=1, le=10)
    tags: Optional[List[str]] = None


@router.get("/stats")
def get_task_stats(conn=Depends(get_db)):
    """Return queue statistics by status and task type."""
    return get_queue_stats(conn)


@router.get("/")
def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    task_type: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn=Depends(get_db),
):
    """List tasks with optional filtering."""
    clauses = []
    params = []

    if status_filter:
        clauses.append("status = %s")
        params.append(status_filter.upper())
    if task_type:
        clauses.append("task_type = %s")
        params.append(task_type.upper())
    if batch_id:
        clauses.append("batch_id = %s::uuid")
        params.append(batch_id)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT task_id, task_type, priority, status, attempt_count, max_attempts,
                   idempotency_key, assigned_worker, scheduled_for, created_at,
                   started_at, completed_at, last_error, batch_id, tags
            FROM task_queue
            {where}
            ORDER BY priority DESC, scheduled_for ASC
            LIMIT %s OFFSET %s;
            """,
            params,
        )
        rows = cur.fetchall()
    return [
        {
            "task_id": str(r[0]),
            "task_type": r[1],
            "priority": r[2],
            "status": r[3],
            "attempt_count": r[4],
            "max_attempts": r[5],
            "idempotency_key": r[6],
            "assigned_worker": r[7],
            "scheduled_for": r[8].isoformat() if r[8] else None,
            "created_at": r[9].isoformat() if r[9] else None,
            "started_at": r[10].isoformat() if r[10] else None,
            "completed_at": r[11].isoformat() if r[11] else None,
            "last_error": r[12],
            "batch_id": str(r[13]) if r[13] else None,
            "tags": r[14],
        }
        for r in rows
    ]


@router.post("/enqueue", status_code=status.HTTP_201_CREATED)
def enqueue_single_task(
    req: EnqueueRequest,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Enqueue a single task. Idempotent on duplicate idempotency_key."""
    if req.task_type not in VALID_TASK_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown task_type: {req.task_type}. Valid types: {sorted(VALID_TASK_TYPES)}",
        )
    task_id = enqueue_task(
        conn=conn,
        task_type=req.task_type,
        payload=req.payload,
        idempotency_key=req.idempotency_key,
        priority=req.priority,
        scenario_id=req.scenario_id,
        max_attempts=req.max_attempts,
        tags=req.tags,
    )
    conn.commit()
    return {"task_id": task_id, "status": "enqueued"}


@router.get("/{task_id}")
def get_task(task_id: str, conn=Depends(get_db)):
    """Get full task details including result and error."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT task_id, task_type, priority, payload, status, attempt_count,
                   max_attempts, assigned_worker, lease_expires_at, idempotency_key,
                   result, last_error, created_at, started_at, completed_at,
                   scheduled_for, batch_id, tags
            FROM task_queue WHERE task_id = %s::uuid;
            """,
            (task_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {
        "task_id": str(row[0]),
        "task_type": row[1],
        "priority": row[2],
        "payload": row[3],
        "status": row[4],
        "attempt_count": row[5],
        "max_attempts": row[6],
        "assigned_worker": row[7],
        "lease_expires_at": row[8].isoformat() if row[8] else None,
        "idempotency_key": row[9],
        "result": row[10],
        "last_error": row[11],
        "created_at": row[12].isoformat() if row[12] else None,
        "started_at": row[13].isoformat() if row[13] else None,
        "completed_at": row[14].isoformat() if row[14] else None,
        "scheduled_for": row[15].isoformat() if row[15] else None,
        "batch_id": str(row[16]) if row[16] else None,
        "tags": row[17],
    }


@router.post("/{task_id}/cancel")
def cancel_task_endpoint(
    task_id: str,
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Cancel a PENDING or RETRYING task."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE task_queue
            SET status = 'CANCELLED', updated_at = NOW()
            WHERE task_id = %s::uuid AND status IN ('PENDING', 'RETRYING')
            RETURNING task_id;
            """,
            (task_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found or not in cancellable state (PENDING/RETRYING)",
        )
    conn.commit()
    return {"task_id": task_id, "status": "cancelled"}


@router.get("/batches/")
def list_batches(
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_db),
):
    """List task batches with progress stats."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT b.batch_id, b.batch_name, b.batch_type, b.status,
                   b.total_tasks, b.created_at, b.completed_at,
                   count(t.task_id) FILTER (WHERE t.status = 'COMPLETED') AS completed_count,
                   count(t.task_id) FILTER (WHERE t.status = 'FAILED') AS failed_count,
                   count(t.task_id) FILTER (WHERE t.status = 'PENDING') AS pending_count
            FROM task_batches b
            LEFT JOIN task_queue t ON t.batch_id = b.batch_id
            GROUP BY b.batch_id, b.batch_name, b.batch_type, b.status,
                     b.total_tasks, b.created_at, b.completed_at
            ORDER BY b.created_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
    return [
        {
            "batch_id": str(r[0]),
            "batch_name": r[1],
            "batch_type": r[2],
            "status": r[3],
            "total_tasks": r[4],
            "created_at": r[5].isoformat() if r[5] else None,
            "completed_at": r[6].isoformat() if r[6] else None,
            "completed_count": r[7] or 0,
            "failed_count": r[8] or 0,
            "pending_count": r[9] or 0,
            "completion_pct": round((r[7] or 0) / max(r[4], 1) * 100, 1),
        }
        for r in rows
    ]


@router.post("/batches/generate")
def generate_demo_backlog(
    batch_name: str = Query("P4-DEMO-BACKLOG", description="Batch name"),
    current_user: AuthUser = Depends(require_role(UserRole.OPERATOR)),
    conn=Depends(get_db),
):
    """Generate ~1,000 diverse tasks across scenario templates for demo/testing."""
    try:
        result = generate_1000_task_backlog(conn, batch_name)
        return result
    except Exception as exc:
        logger.error("Failed to generate backlog: %s", exc)
        raise HTTPException(status_code=500, detail=f"Backlog generation failed: {exc}")


@router.get("/worker/status")
def get_worker_status():
    """Return in-process task worker status."""
    worker = get_default_worker()
    if worker is None:
        return {"running": False, "reason": "Worker not started"}
    return worker.get_status()
