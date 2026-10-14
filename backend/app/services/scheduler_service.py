"""Persistent Scenario Scheduler Service.

Manages recurring scenario execution with:
- Configurable interval (defaults to 300 seconds, overridden by env var)
- Cross-process lease locking in PostgreSQL to prevent concurrent runs across workers
- Stale-lock recovery if a worker crashes
- Intelligent scenario eligibility based on enabled scenario_templates
- Duplicate prevention (never triggers scenarios that are already actively running)
- Honest NO_WORK reporting when no eligible scenarios require execution
- Graceful startup and shutdown for FastAPI application lifecycle
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.db.database import get_db_connection
from app.models.workflow import WorkflowCreateRequest
from app.orchestration.graph import WorkflowGraph
from app.services.workflow_service import create_workflow

logger = logging.getLogger("enterpriseai.scheduler")

SCHEDULER_NAME = "scenario-generator"
DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_LEASE_SECONDS = 60


def get_configured_interval() -> int:
    """Retrieve validated scheduler interval in seconds from environment or default."""
    raw = os.environ.get("SCHEDULER_INTERVAL_SECONDS") or os.environ.get("SCENARIO_SCHEDULER_INTERVAL_SECONDS")
    if raw:
        try:
            val = int(raw.strip())
            if val >= 5:  # Allow fast testing intervals (>=5s), defaults to 300s
                return val
        except ValueError:
            pass
    return DEFAULT_INTERVAL_SECONDS


def is_scheduler_enabled() -> bool:
    """Check whether scheduler background loop is enabled. Defaults to false in test suite."""
    import sys
    if "pytest" in sys.modules:
        return os.environ.get("SCHEDULER_ENABLED", "false").strip().lower() in {"true", "1", "yes", "on"}
    val = os.environ.get("SCHEDULER_ENABLED", "true").strip().lower()
    return val in {"true", "1", "yes", "on"}


class ScenarioScheduler:
    """Coordinator for scheduled scenario generation with PostgreSQL lease locking."""

    def __init__(self, scheduler_name: str = SCHEDULER_NAME):
        self.scheduler_name = scheduler_name
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def acquire_lease(
        self,
        conn,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> Tuple[bool, Optional[int]]:
        """Try to acquire or renew the distributed lease in PostgreSQL.

        Recovers stale locks if lease_expires_at < NOW().
        Returns (acquired: bool, interval_seconds: Optional[int]).
        """
        now = datetime.now(timezone.utc)
        sql = """
            UPDATE scheduler_state
            SET
                locked_by = %s,
                lock_acquired_at = %s,
                lease_expires_at = %s + (%s || ' seconds')::interval,
                updated_at = %s
            WHERE scheduler_name = %s
              AND enabled = TRUE
              AND (
                  lease_expires_at IS NULL
                  OR lease_expires_at < %s
                  OR locked_by = %s
              )
            RETURNING interval_seconds, enabled;
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    self.worker_id,
                    now,
                    now,
                    str(lease_seconds),
                    now,
                    self.scheduler_name,
                    now,
                    self.worker_id,
                ),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return True, row[0]
            conn.rollback()
            return False, None

    def release_lease(
        self,
        conn,
        outcome_status: str,
        scenario_id: Optional[str] = None,
        next_interval: Optional[int] = None,
    ) -> None:
        """Release the acquired lease and update last/next scheduled timestamps."""
        now = datetime.now(timezone.utc)
        interval = next_interval or get_configured_interval()
        sql = """
            UPDATE scheduler_state
            SET
                locked_by = NULL,
                lease_expires_at = NULL,
                last_scheduled_at = %s,
                next_scheduled_at = %s + (%s || ' seconds')::interval,
                last_status = %s,
                last_scenario_id = %s,
                total_runs = total_runs + 1,
                consecutive_failures = CASE WHEN %s = 'FAILED' THEN consecutive_failures + 1 ELSE 0 END,
                updated_at = %s
            WHERE scheduler_name = %s AND locked_by = %s;
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    now,
                    now,
                    str(interval),
                    outcome_status,
                    scenario_id,
                    outcome_status,
                    now,
                    self.scheduler_name,
                    self.worker_id,
                ),
            )
            conn.commit()

    def find_eligible_scenario(self, conn) -> Optional[Tuple[str, str, str]]:
        """Identify the next enabled scenario template that has no active workflow running.

        Returns (template_id, scenario_type, severity) or None.
        """
        sql = """
            SELECT
                st.scenario_template_id,
                st.scenario_type,
                st.severity
            FROM scenario_templates st
            WHERE st.enabled = TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM scenario_instances si
                  WHERE si.scenario_template_id = st.scenario_template_id
                    AND si.status IN ('QUEUED', 'RUNNING', 'INVESTIGATING', 'EXECUTING', 'WAITING_APPROVAL')
              )
            ORDER BY st.scenario_template_id ASC
            LIMIT 1;
        """
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()

    def run_cycle(self, conn, force: bool = False) -> Dict[str, Any]:
        """Execute one complete scheduler cycle with lease locking and eligibility check."""
        acquired, db_interval = self.acquire_lease(conn)
        if not acquired and not force:
            logger.info("Scheduler lease currently held by another worker; skipping cycle.")
            return {
                "executed": False,
                "reason": "LEASE_HELD_BY_OTHER",
                "worker_id": self.worker_id,
            }

        try:
            eligible = self.find_eligible_scenario(conn)
            if not eligible:
                logger.info("No eligible scenarios found with pending work; recording NO_WORK.")
                self.release_lease(conn, outcome_status="NO_WORK", scenario_id=None, next_interval=db_interval)
                return {
                    "executed": False,
                    "reason": "NO_ELIGIBLE_SCENARIOS",
                    "status": "NO_WORK",
                    "worker_id": self.worker_id,
                }

            template_id, scenario_type, severity = eligible
            logger.info("Scheduler triggering eligible scenario %s (%s, %s)", template_id, scenario_type, severity)

            # Persist and execute workflow
            create_req = WorkflowCreateRequest(
                scenario_template_id=template_id,
                linked_order_id=f"SCHED-ORD-{uuid.uuid4().hex[:6].upper()}",
                severity=severity,
                input_overlay={"scheduled_by": self.scheduler_name, "worker_id": self.worker_id},
                execute_immediately=True,
            )
            workflow = create_workflow(conn, create_req)

            # Execute specialist agents
            graph = WorkflowGraph()
            initial_state = {
                "workflow_id": workflow.workflow_id,
                "scenario_id": workflow.scenario_id,
                "order_id": workflow.linked_order_id,
                "current_agent": "SupervisorAgent",
                "status": "queued",
                "audit_trail": [],
            }
            res_state = graph.run_workflow(initial_state, conn=conn)
            final_status = "COMPLETED" if res_state.get("status") == "completed" else "FAILED"

            self.release_lease(
                conn,
                outcome_status=final_status,
                scenario_id=workflow.scenario_id,
                next_interval=db_interval,
            )

            return {
                "executed": True,
                "status": final_status,
                "scenario_id": workflow.scenario_id,
                "template_id": template_id,
                "order_id": workflow.linked_order_id,
                "worker_id": self.worker_id,
            }
        except Exception as exc:
            logger.error("Error during scheduler cycle: %s", exc)
            try:
                self.release_lease(conn, outcome_status="FAILED", scenario_id=None, next_interval=db_interval)
            except Exception:
                pass
            return {
                "executed": False,
                "status": "FAILED",
                "error": str(exc),
                "worker_id": self.worker_id,
            }

    def get_status(self, conn) -> Dict[str, Any]:
        """Fetch current scheduler configuration and execution statistics."""
        sql = """
            SELECT
                scheduler_name, enabled, interval_seconds,
                last_scheduled_at, next_scheduled_at, updated_at,
                locked_by, lease_expires_at, last_status,
                last_scenario_id, total_runs, consecutive_failures
            FROM scheduler_state
            WHERE scheduler_name = %s;
        """
        with conn.cursor() as cur:
            cur.execute(sql, (self.scheduler_name,))
            row = cur.fetchone()
            if not row:
                return {
                    "scheduler_name": self.scheduler_name,
                    "enabled": False,
                    "status": "NOT_FOUND",
                }

            now = datetime.now(timezone.utc)
            lease_expires = row[7]
            is_currently_locked = bool(row[6] and lease_expires and lease_expires > now)

            return {
                "scheduler_name": row[0],
                "enabled": row[1],
                "configured_interval_seconds": row[2],
                "last_scheduled_at": row[3].isoformat() if row[3] else None,
                "next_scheduled_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "is_locked": is_currently_locked,
                "locked_by": row[6] if is_currently_locked else None,
                "lease_expires_at": lease_expires.isoformat() if lease_expires else None,
                "last_status": row[8],
                "last_scenario_id": str(row[9]) if row[9] else None,
                "total_runs": row[10],
                "consecutive_failures": row[11],
                "background_worker_active": self._running,
            }

    async def _loop(self):
        """Asynchronous background loop honoring configured interval and cancellations."""
        interval = get_configured_interval()
        logger.info("Starting background scheduler loop with %ds interval", interval)
        self._running = True
        try:
            while self._running:
                await asyncio.sleep(interval)
                if not self._running:
                    break
                try:
                    with get_db_connection() as conn:
                        self.run_cycle(conn)
                except Exception as exc:
                    logger.warning("Scheduler loop execution encountered error: %s", exc)
        except asyncio.CancelledError:
            logger.info("Scheduler background loop cancelled cleanly.")
        finally:
            self._running = False

    def start(self):
        """Start the background task loop in current asyncio event loop."""
        if not is_scheduler_enabled():
            logger.info("Scheduler disabled via SCHEDULER_ENABLED=false; loop not started.")
            return
        if self._task is None or self._task.done():
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._loop())

    def stop(self):
        """Gracefully stop the background task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None


# Singleton scheduler instance for application
default_scheduler = ScenarioScheduler()
