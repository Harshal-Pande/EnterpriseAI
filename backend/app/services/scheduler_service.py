"""Persistent Scenario Scheduler and Generation Engine (Phase 3).

Manages recurring autonomous scenario execution with:
- Configurable interval (defaults to 300 seconds, strict env precedence)
- Cross-process lease locking in PostgreSQL with stale-lock recovery
- Configurable open-scenario capacity limits (SCHEDULER_MAX_OPEN_SCENARIOS)
- Real PostgreSQL operational data grounding (no fabricated entity IDs)
- Deterministic and seeded scenario template selection
- Cycle-level idempotency to prevent duplicate instances across restarts
- Event audit logging in event_log (cycle started, lease acquired/released, generation, skips)
- Graceful startup, loop execution, and cancellation without leaks
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.events import EventChannel, EventType, default_event_manager
from app.core.sanitizer import sanitize_dict
from app.db.database import get_db_connection
from app.models.workflow import WorkflowCreateRequest
from app.orchestration.graph import WorkflowGraph
from app.services.workflow_service import create_workflow

logger = logging.getLogger("enterpriseai.scheduler")

SCHEDULER_NAME = "scenario-generator"
DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_LEASE_SECONDS = 60
DEFAULT_MAX_OPEN_SCENARIOS = 10
DEFAULT_STALE_TIMEOUT_SECONDS = 300


def get_configured_interval() -> int:
    """Retrieve validated scheduler interval in seconds from environment with strict precedence:
    SCENARIO_SCHEDULER_INTERVAL_SECONDS takes precedence over SCHEDULER_INTERVAL_SECONDS.
    Defaults to 300 seconds. Accepts >= 1 for accelerated testing.
    """
    raw = os.environ.get("SCENARIO_SCHEDULER_INTERVAL_SECONDS") or os.environ.get("SCHEDULER_INTERVAL_SECONDS")
    if raw is not None and raw.strip():
        try:
            val = int(raw.strip())
            if 1 <= val <= 86400:
                return val
            logger.warning(
                "Configured scheduler interval %d out of bounds (1..86400); using default %ds",
                val,
                DEFAULT_INTERVAL_SECONDS,
            )
        except ValueError:
            logger.warning(
                "Invalid scheduler interval '%s'; using default %ds",
                raw,
                DEFAULT_INTERVAL_SECONDS,
            )
    return DEFAULT_INTERVAL_SECONDS


def get_max_open_scenarios() -> int:
    """Retrieve configured maximum active open scenarios allowed in the queue."""
    raw = os.environ.get("SCHEDULER_MAX_OPEN_SCENARIOS")
    if raw is not None and raw.strip():
        try:
            val = int(raw.strip())
            if val >= 1:
                return val
        except ValueError:
            pass
    return DEFAULT_MAX_OPEN_SCENARIOS


def get_lease_duration_seconds() -> int:
    """Retrieve distributed lock lease duration in seconds (default: 60s)."""
    raw = os.environ.get("SCHEDULER_LEASE_SECONDS")
    if raw is not None and raw.strip():
        try:
            val = int(raw.strip())
            if 5 <= val <= 3600:
                return val
        except ValueError:
            pass
    return DEFAULT_LEASE_SECONDS


def get_workflow_stale_timeout_seconds() -> int:
    """Retrieve configurable stale timeout in seconds for orphaned workflows.
    Defaults to 300 seconds. Accepts >= 1 for accelerated tests.
    """
    raw = os.environ.get("WORKFLOW_STALE_TIMEOUT_SECONDS") or os.environ.get("SCHEDULER_STALE_TIMEOUT_SECONDS")
    if raw is not None and raw.strip():
        try:
            val = int(raw.strip())
            if val >= 1:
                return val
        except ValueError:
            pass
    return DEFAULT_STALE_TIMEOUT_SECONDS


def get_lease_renewal_interval_seconds() -> float:
    """Retrieve lease renewal heartbeat interval in seconds.
    Defaults to 1/4 of the lease duration (e.g. 15s for 60s lease).
    Accepts >= 0.05 for tests.
    """
    raw = os.environ.get("SCHEDULER_LEASE_RENEWAL_INTERVAL_SECONDS")
    if raw is not None and raw.strip():
        try:
            val = float(raw.strip())
            if val >= 0.05:
                return val
        except ValueError:
            pass
    return max(1.0, get_lease_duration_seconds() / 4.0)


def is_scheduler_enabled() -> bool:
    """Check whether scheduler background loop is enabled. Defaults to false in test suite."""
    import sys
    if "pytest" in sys.modules:
        return os.environ.get("SCHEDULER_ENABLED", "false").strip().lower() in {"true", "1", "yes", "on"}
    val = os.environ.get("SCHEDULER_ENABLED", "true").strip().lower()
    return val in {"true", "1", "yes", "on"}


def count_open_scenarios(conn) -> int:
    """Count scenarios in non-terminal active states."""
    sql = """
        SELECT count(*)
        FROM scenario_instances
        WHERE status IN ('QUEUED', 'RUNNING', 'INVESTIGATING', 'EXECUTING', 'WAITING_APPROVAL');
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        return int(row[0]) if row else 0


def log_scheduler_event(
    conn,
    event_type: str,
    status: str,
    entity_id: str,
    scenario_id: Optional[str] = None,
    evidence_refs: Optional[Dict[str, Any]] = None,
    reason_code: Optional[str] = None,
    actor_id: str = "scheduler-engine",
) -> None:
    """Helper to persist audit events directly into event_log."""
    try:
        event_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        payload = evidence_refs or {}
        serialized = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_log (
                    event_id, event_timestamp, event_type, entity_type, entity_id,
                    scenario_id, actor_type, actor_id, status,
                    reason_code, evidence_refs, payload_hash, source_channel
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    str(event_id),
                    now,
                    event_type,
                    "SCHEDULER",
                    entity_id,
                    scenario_id,
                    "SYSTEM",
                    actor_id,
                    status,
                    reason_code,
                    json.dumps(payload),
                    payload_hash,
                    "SCHEDULER_DAEMON",
                ),
            )
            conn.commit()

            default_event_manager.publish(
                event_type=event_type,
                channel=EventChannel.SCHEDULER.value,
                entity_id=entity_id,
                entity_type="SCHEDULER",
                scenario_id=scenario_id,
                payload={"status": status, "reason_code": reason_code, **(payload if isinstance(payload, dict) else {})},
            )
    except Exception as exc:
        logger.warning("Failed to log scheduler event %s: %s", event_type, exc)


def ground_operational_reference(
    conn,
    template_id: str,
    scenario_type: str,
) -> Tuple[str, Dict[str, Any]]:
    """Query real PostgreSQL operational tables to bind the scenario to genuine entities."""
    with conn.cursor() as cur:
        # Default fallback order from operational database
        cur.execute(
            """
            SELECT order_id, customer_ref, status
            FROM orders
            WHERE status IN ('OPEN', 'IN_PROGRESS', 'PENDING', 'PROCESSING')
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT order_id, customer_ref, status FROM orders ORDER BY order_id LIMIT 1;")
            row = cur.fetchone()

        default_order_id = row[0] if row else "ORD-001"
        grounded_data: Dict[str, Any] = {"order_id": default_order_id}

        # Template-specific grounding against seeded tables
        if scenario_type in {"INVENTORY_SHORTAGE", "SPARE_PART_SHORTAGE"}:
            cur.execute(
                """
                SELECT item_id, warehouse_id, available_qty, on_hand_qty, reserved_qty
                FROM inventory
                WHERE available_qty > 0
                ORDER BY available_qty ASC
                LIMIT 1;
                """
            )
            inv_row = cur.fetchone()
            if inv_row:
                grounded_data["item_id"] = inv_row[0]
                grounded_data["warehouse_id"] = inv_row[1]
                grounded_data["available_qty"] = float(inv_row[2])
                grounded_data["on_hand_qty"] = float(inv_row[3])
                grounded_data["reserved_qty"] = float(inv_row[4])
                grounded_data["shortage_qty"] = max(10.0, float(inv_row[4]) - float(inv_row[2]) + 25.0)

        elif scenario_type in {"SUPPLIER_UNAVAILABLE", "SUPPLIER_RECERTIFICATION"}:
            cur.execute(
                """
                SELECT supplier_id, supplier_name, supplier_category, status
                FROM suppliers
                WHERE status = 'ACTIVE'
                ORDER BY supplier_id ASC
                LIMIT 1;
                """
            )
            supp_row = cur.fetchone()
            if supp_row:
                grounded_data["supplier_id"] = supp_row[0]
                grounded_data["supplier_name"] = supp_row[1]
                grounded_data["category"] = supp_row[2]

        elif scenario_type in {"BUDGET_BREACH"}:
            cur.execute(
                """
                SELECT budget_id, cost_center, available_budget_inr, single_action_approval_threshold_inr
                FROM budgets
                WHERE status = 'ACTIVE'
                ORDER BY available_budget_inr DESC
                LIMIT 1;
                """
            )
            budg_row = cur.fetchone()
            if budg_row:
                grounded_data["budget_id"] = budg_row[0]
                grounded_data["department"] = budg_row[1]
                grounded_data["available_budget"] = float(budg_row[2])
                grounded_data["threshold_inr"] = float(budg_row[3])

        elif scenario_type in {"DELIVERY_DELAY"}:
            cur.execute(
                """
                SELECT order_id, customer_ref, required_delivery_at
                FROM orders
                WHERE status IN ('OPEN', 'IN_PROGRESS')
                ORDER BY created_at ASC
                LIMIT 1;
                """
            )
            delay_row = cur.fetchone()
            if delay_row:
                grounded_data["order_id"] = delay_row[0]
                grounded_data["delivery_corridor"] = "NH-53 Pune-Nagpur"
                grounded_data["delay_hours"] = 48

        elif scenario_type in {"QUALITY_HOLD", "RAW_MATERIAL_QUALITY"}:
            cur.execute("SELECT item_id, warehouse_id FROM inventory LIMIT 1;")
            q_row = cur.fetchone()
            if q_row:
                grounded_data["item_id"] = q_row[0]
                grounded_data["warehouse_id"] = q_row[1]
                grounded_data["quality_defect"] = "Surface micro-fracture / tolerance deviation"

        return grounded_data.get("order_id", default_order_id), grounded_data


class ScenarioScheduler:
    """Coordinator for scheduled scenario generation with PostgreSQL lease locking."""

    def __init__(self, scheduler_name: str = SCHEDULER_NAME):
        self.scheduler_name = scheduler_name
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_skip_reason: Optional[str] = None

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
        skip_reason: Optional[str] = None,
    ) -> None:
        """Release the acquired lease and update last/next scheduled timestamps."""
        now = datetime.now(timezone.utc)
        interval = next_interval or get_configured_interval()
        self._last_skip_reason = skip_reason
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

    def renew_lease(
        self,
        conn,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> bool:
        """Renew the currently held lease if still owned by this worker.

        Returns True if renewed, False if lease was lost, expired, or reassigned.
        """
        now = datetime.now(timezone.utc)
        sql = """
            UPDATE scheduler_state
            SET
                lease_expires_at = %s + (%s || ' seconds')::interval,
                updated_at = %s
            WHERE scheduler_name = %s
              AND locked_by = %s
              AND enabled = TRUE
            RETURNING locked_by;
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    now,
                    str(lease_seconds),
                    now,
                    self.scheduler_name,
                    self.worker_id,
                ),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return True
            conn.rollback()
            return False

    @contextmanager
    def lease_heartbeat(
        self,
        lease_seconds: Optional[int] = None,
        interval: Optional[float] = None,
    ):
        """Context manager running a periodic background renewal heartbeat while workflow executes.

        Ensures lease does not expire during long-running execution, detects ownership loss,
        and shuts down cleanly without leaking threads.
        """
        effective_lease_sec = lease_seconds or get_lease_duration_seconds()
        renewal_interval = interval or get_lease_renewal_interval_seconds()
        stop_event = threading.Event()
        self._lease_lost = False

        def _worker():
            while not stop_event.is_set():
                if stop_event.wait(timeout=renewal_interval):
                    break
                try:
                    with get_db_connection() as heartbeat_conn:
                        renewed = self.renew_lease(heartbeat_conn, lease_seconds=effective_lease_sec)
                        if not renewed:
                            logger.warning(
                                "Worker %s failed to renew scheduler lease; ownership lost or expired.",
                                self.worker_id,
                            )
                            self._lease_lost = True
                            break
                except Exception as exc:
                    logger.warning("Error during lease heartbeat renewal: %s", exc)

        t = threading.Thread(target=_worker, daemon=True, name=f"lease-heartbeat-{self.worker_id}")
        t.start()
        try:
            yield
        finally:
            stop_event.set()
            t.join(timeout=2.0)

        if getattr(self, "_lease_lost", False):
            raise RuntimeError(f"Scheduler lease ownership was lost during execution by {self.worker_id}")

    def recover_orphaned_workflows(
        self,
        conn,
        stale_timeout_seconds: Optional[int] = None,
    ) -> List[str]:
        """Safely recover scenarios left in QUEUED or RUNNING states after a worker or process crash.

        Uses FOR UPDATE SKIP LOCKED to ensure concurrent recovery passes cannot conflict.
        Transitions orphans to 'FAILED' with reason 'STALE_WORKFLOW_TIMEOUT'.
        Returns list of recovered scenario IDs.
        """
        timeout_sec = stale_timeout_seconds or get_workflow_stale_timeout_seconds()
        now = datetime.now(timezone.utc)
        recovered_ids: List[str] = []

        try:
            sql_select = """
                SELECT scenario_id, status, scenario_template_id, linked_order_id, updated_at
                FROM scenario_instances
                WHERE status IN ('QUEUED', 'RUNNING')
                  AND updated_at < %s - (%s || ' seconds')::interval
                ORDER BY updated_at ASC
                FOR UPDATE SKIP LOCKED;
            """
            with conn.cursor() as cur:
                cur.execute(sql_select, (now, str(timeout_sec)))
                rows = cur.fetchall()
                if not rows:
                    return []

                sql_update = """
                    UPDATE scenario_instances
                    SET
                        status = 'FAILED',
                        resolved_at = %s,
                        resolution_summary = %s,
                        updated_at = %s
                    WHERE scenario_id = %s;
                """
                for r in rows:
                    scen_id, prev_status, tpl_id, order_id, updated_at = r
                    summary = f"Orphaned workflow recovered by watchdog: status '{prev_status}' timed out after {timeout_sec}s"
                    cur.execute(sql_update, (now, summary, now, scen_id))
                    recovered_ids.append(str(scen_id))

                    log_scheduler_event(
                        conn,
                        event_type="ORPHANED_WORKFLOW_RECOVERED",
                        status="FAILED",
                        entity_id=str(scen_id),
                        scenario_id=str(scen_id),
                        reason_code="STALE_WORKFLOW_TIMEOUT",
                        evidence_refs={
                            "previous_status": prev_status,
                            "stale_timeout_seconds": timeout_sec,
                            "scenario_template_id": tpl_id,
                            "linked_order_id": order_id,
                            "last_updated_at": updated_at.isoformat() if updated_at else None,
                        },
                        actor_id="scheduler-watchdog",
                    )
            conn.commit()
            if recovered_ids:
                logger.warning(
                    "Recovered %d orphaned workflows exceeding %ds timeout: %s",
                    len(recovered_ids),
                    timeout_sec,
                    recovered_ids,
                )
        except Exception as exc:
            conn.rollback()
            logger.error("Failed during orphaned workflow recovery: %s", exc)

        return recovered_ids

    def find_eligible_scenario(
        self,
        conn,
        seed: Optional[int] = None,
    ) -> Optional[Tuple[str, str, str]]:
        """Identify the next enabled scenario template that has no active workflow running.

        Supports deterministic seeded selection if seed is provided or SCHEDULER_RANDOM_SEED is set.
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
            ORDER BY st.scenario_template_id ASC;
        """
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            if not rows:
                return None

            chosen_seed = seed
            if chosen_seed is None:
                seed_env = os.environ.get("SCHEDULER_RANDOM_SEED")
                if seed_env and seed_env.strip().isdigit():
                    chosen_seed = int(seed_env.strip())

            if chosen_seed is not None:
                idx = chosen_seed % len(rows)
                return rows[idx]

            return rows[0]

    def get_template_by_id(
        self,
        conn,
        template_id: str,
    ) -> Optional[Tuple[str, str, str]]:
        """Retrieve an enabled scenario template by its ID."""
        sql = """
            SELECT scenario_template_id, scenario_type, severity
            FROM scenario_templates
            WHERE scenario_template_id = %s AND enabled = TRUE;
        """
        with conn.cursor() as cur:
            cur.execute(sql, (template_id,))
            return cur.fetchone()

    def run_cycle(
        self,
        conn,
        force: bool = False,
        admin_override: bool = False,
        override_reason: Optional[str] = None,
        template_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        seed: Optional[int] = None,
        is_manual: bool = False,
        actor_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute one complete scheduler cycle with lease locking, limit gating, grounding, and persistence.

        Hardened Guarantees:
        - Safe recovery of stale/orphaned workflows is performed before work execution.
        - Mutual exclusion is absolute: force/override CANNOT bypass an active lease held by another worker.
        - Automated scheduled ticks derive deterministic slot idempotency from configured interval.
        - Background lease renewal heartbeat prevents lease expiration during execution.
        - Administrative override allows bypassing queue capacity ONLY when explicitly authorized with audit reason.
        """
        # Always run recovery of stale orphaned workflows first
        self.recover_orphaned_workflows(conn)

        lease_sec = get_lease_duration_seconds()
        acquired, db_interval = self.acquire_lease(conn, lease_seconds=lease_sec)
        effective_interval = db_interval or get_configured_interval()

        # FIND-01 Fix: Never allow force or admin_override to bypass lease mutual exclusion
        if not acquired:
            logger.info("Scheduler lease currently held by another worker; skipping cycle.")
            self._last_skip_reason = "LEASE_HELD_BY_OTHER"
            log_scheduler_event(
                conn,
                event_type="SCENARIO_GENERATION_SKIPPED",
                status="SKIPPED",
                entity_id=self.scheduler_name,
                reason_code="LEASE_HELD_BY_OTHER",
                evidence_refs={
                    "worker_id": self.worker_id,
                    "force": force,
                    "admin_override": admin_override,
                },
                actor_id=actor_id or self.worker_id,
            )
            return {
                "executed": False,
                "status": "SKIPPED",
                "reason": "LEASE_HELD_BY_OTHER",
                "worker_id": self.worker_id,
            }

        log_scheduler_event(
            conn,
            event_type="SCHEDULER_CYCLE_STARTED",
            status="IN_PROGRESS",
            entity_id=self.scheduler_name,
            evidence_refs={
                "worker_id": self.worker_id,
                "force": force,
                "admin_override": admin_override,
                "is_manual": is_manual,
            },
            actor_id=actor_id or self.worker_id,
        )

        try:
            # 1. Enforce active open scenarios limit
            open_count = count_open_scenarios(conn)
            max_open = get_max_open_scenarios()
            can_override_capacity = admin_override or (force and bool(override_reason and override_reason.strip()))

            if open_count >= max_open:
                if not can_override_capacity:
                    logger.info(
                        "Open scenario queue capacity reached (%d/%d); skipping generation.",
                        open_count,
                        max_open,
                    )
                    self._last_skip_reason = "OPEN_SCENARIOS_LIMIT_REACHED"
                    self.release_lease(
                        conn,
                        outcome_status="SKIPPED",
                        scenario_id=None,
                        next_interval=effective_interval,
                        skip_reason="OPEN_SCENARIOS_LIMIT_REACHED",
                    )
                    log_scheduler_event(
                        conn,
                        event_type="SCENARIO_GENERATION_SKIPPED",
                        status="SKIPPED",
                        entity_id=self.scheduler_name,
                        reason_code="OPEN_SCENARIOS_LIMIT_REACHED",
                        evidence_refs={"open_count": open_count, "max_open": max_open},
                        actor_id=actor_id or self.worker_id,
                    )
                    return {
                        "executed": False,
                        "status": "SKIPPED",
                        "reason": "OPEN_SCENARIOS_LIMIT_REACHED",
                        "open_count": open_count,
                        "max_open": max_open,
                        "worker_id": self.worker_id,
                    }
                else:
                    log_scheduler_event(
                        conn,
                        event_type="ADMIN_CAPACITY_OVERRIDE",
                        status="OVERRIDDEN",
                        entity_id=self.scheduler_name,
                        reason_code="CAPACITY_LIMIT_BYPASSED",
                        evidence_refs={
                            "open_count": open_count,
                            "max_open": max_open,
                            "override_reason": override_reason or "Admin override",
                            "actor_id": actor_id or self.worker_id,
                        },
                        actor_id=actor_id or self.worker_id,
                    )

            # 2. Check explicit caller-provided idempotency key if present
            if idempotency_key:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT scenario_id, status, linked_order_id, scenario_template_id
                        FROM scenario_instances
                        WHERE idempotency_key = %s;
                        """,
                        (idempotency_key,),
                    )
                    existing = cur.fetchone()
                    if existing:
                        logger.info(
                            "Cycle idempotency hit for key '%s'; returning existing scenario %s.",
                            idempotency_key,
                            existing[0],
                        )
                        self.release_lease(
                            conn,
                            outcome_status="IDEMPOTENT_HIT",
                            scenario_id=str(existing[0]),
                            next_interval=effective_interval,
                        )
                        return {
                            "executed": False,
                            "status": "EXISTING_INSTANCE",
                            "scenario_id": str(existing[0]),
                            "template_id": existing[3],
                            "order_id": existing[2],
                            "reason": "IDEMPOTENT_EXISTING",
                            "worker_id": self.worker_id,
                        }

            # 3. Find or validate eligible scenario template
            eligible = None
            if template_id:
                eligible = self.get_template_by_id(conn, template_id)
                if not eligible:
                    raise ValueError(f"Requested template '{template_id}' is not enabled or does not exist.")
            else:
                eligible = self.find_eligible_scenario(conn, seed=seed)

            if not eligible:
                logger.info("No eligible scenarios found with pending work; recording NO_WORK.")
                self._last_skip_reason = "NO_ELIGIBLE_TEMPLATES"
                self.release_lease(
                    conn,
                    outcome_status="NO_WORK",
                    scenario_id=None,
                    next_interval=effective_interval,
                    skip_reason="NO_ELIGIBLE_TEMPLATES",
                )
                log_scheduler_event(
                    conn,
                    event_type="SCENARIO_GENERATION_SKIPPED",
                    status="NO_WORK",
                    entity_id=self.scheduler_name,
                    reason_code="NO_ELIGIBLE_TEMPLATES",
                    evidence_refs={"worker_id": self.worker_id},
                    actor_id=actor_id or self.worker_id,
                )
                return {
                    "executed": False,
                    "reason": "NO_ELIGIBLE_SCENARIOS",
                    "status": "NO_WORK",
                    "worker_id": self.worker_id,
                }

            sel_template_id, scenario_type, severity = eligible
            logger.info("Scheduler triggering eligible scenario %s (%s, %s)", sel_template_id, scenario_type, severity)

            # 4. Ground against real operational entities in PostgreSQL
            linked_order_id, grounded_data = ground_operational_reference(conn, sel_template_id, scenario_type)

            # FIND-02 Fix: Deterministic scheduled idempotency derived from UTC slot & template
            if idempotency_key:
                cycle_idemp = idempotency_key
            elif is_manual:
                cycle_idemp = f"MANUAL-{sel_template_id}-{uuid.uuid4().hex[:12]}"
            else:
                now_ts = int(datetime.now(timezone.utc).timestamp())
                slot_ts = (now_ts // effective_interval) * effective_interval
                cycle_idemp = f"SCHED-{sel_template_id}-SLOT-{slot_ts}"

            # Precheck deterministic cycle idempotency before creating instance
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT scenario_id, status, linked_order_id, scenario_template_id
                    FROM scenario_instances
                    WHERE idempotency_key = %s;
                    """,
                    (cycle_idemp,),
                )
                existing_slot = cur.fetchone()
                if existing_slot:
                    logger.info(
                        "Slot idempotency hit for key '%s'; returning existing scenario %s.",
                        cycle_idemp,
                        existing_slot[0],
                    )
                    self.release_lease(
                        conn,
                        outcome_status="IDEMPOTENT_HIT",
                        scenario_id=str(existing_slot[0]),
                        next_interval=effective_interval,
                    )
                    return {
                        "executed": False,
                        "status": "EXISTING_INSTANCE",
                        "scenario_id": str(existing_slot[0]),
                        "template_id": existing_slot[3],
                        "order_id": existing_slot[2],
                        "reason": "IDEMPOTENT_EXISTING",
                        "worker_id": self.worker_id,
                    }

            # 5. Persist workflow and scenario instance atomically
            create_req = WorkflowCreateRequest(
                scenario_template_id=sel_template_id,
                linked_order_id=linked_order_id,
                severity=severity,
                input_overlay={
                    "scenario_type": scenario_type,
                    "scheduled_by": self.scheduler_name,
                    "worker_id": self.worker_id,
                    "grounded_data": grounded_data,
                    "generation_metadata": {
                        "grounded_operational_data": True,
                        "template_id": sel_template_id,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "is_manual": is_manual,
                    },
                },
                idempotency_key=cycle_idemp,
                execute_immediately=True,
            )
            workflow = create_workflow(conn, create_req)

            log_scheduler_event(
                conn,
                event_type="SCENARIO_GENERATED",
                status="GENERATED",
                entity_id=workflow.scenario_id,
                scenario_id=workflow.scenario_id,
                evidence_refs={
                    "template_id": sel_template_id,
                    "scenario_type": scenario_type,
                    "severity": severity,
                    "linked_order_id": linked_order_id,
                    "idempotency_key": cycle_idemp,
                    "grounded_data": grounded_data,
                },
                actor_id=actor_id or self.worker_id,
            )

            # 6. Execute specialist agents with active lease renewal heartbeat (FIND-04 Fix)
            with self.lease_heartbeat(lease_seconds=lease_sec):
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
                next_interval=effective_interval,
            )

            log_scheduler_event(
                conn,
                event_type="SCHEDULER_LEASE_RELEASED",
                status=final_status,
                entity_id=self.scheduler_name,
                scenario_id=workflow.scenario_id,
                evidence_refs={"final_status": final_status, "scenario_id": workflow.scenario_id},
                actor_id=actor_id or self.worker_id,
            )

            self._last_skip_reason = None

            return {
                "executed": True,
                "status": final_status,
                "scenario_id": workflow.scenario_id,
                "template_id": sel_template_id,
                "scenario_type": scenario_type,
                "order_id": workflow.linked_order_id,
                "worker_id": self.worker_id,
            }
        except Exception as exc:
            logger.error("Error during scheduler cycle: %s", exc)
            self._last_skip_reason = str(exc)
            try:
                self.release_lease(conn, outcome_status="FAILED", scenario_id=None, next_interval=effective_interval)
                log_scheduler_event(
                    conn,
                    event_type="SCENARIO_GENERATION_FAILED",
                    status="FAILED",
                    entity_id=self.scheduler_name,
                    reason_code=str(exc)[:100],
                    evidence_refs={"error": str(exc), "worker_id": self.worker_id},
                    actor_id=actor_id or self.worker_id,
                )
            except Exception:
                pass
            return {
                "executed": False,
                "status": "FAILED",
                "error": str(exc),
                "worker_id": self.worker_id,
            }

    def get_status(self, conn=None) -> Dict[str, Any]:
        """Fetch current scheduler configuration, open scenario counts, and execution statistics."""
        if conn is None:
            with get_db_connection() as c:
                return self.get_status(c)
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
            open_count = count_open_scenarios(conn)
            max_open = get_max_open_scenarios()
            interval = get_configured_interval()

            last_sched = row[3]
            computed_next_sched = row[4]
            if last_sched and (not computed_next_sched or computed_next_sched < now):
                computed_next_sched = last_sched + timedelta(seconds=interval)

            return {
                "scheduler_name": row[0],
                "enabled": row[1],
                "configured_interval_seconds": interval,
                "interval_seconds": interval,
                "max_open_scenarios": max_open,
                "open_scenarios_count": open_count,
                "last_scheduled_at": last_sched.isoformat() if last_sched else None,
                "last_run_at": last_sched.isoformat() if last_sched else None,
                "next_scheduled_at": computed_next_sched.isoformat() if computed_next_sched else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "is_locked": is_currently_locked,
                "locked_by": row[6] if is_currently_locked else None,
                "lease_expires_at": lease_expires.isoformat() if lease_expires else None,
                "last_status": row[8],
                "last_skip_reason": getattr(self, "_last_skip_reason", None),
                "last_scenario_id": str(row[9]) if row[9] else None,
                "total_runs": row[10],
                "consecutive_failures": row[11],
                "background_worker_active": self._running,
                "is_running": self._running or bool(row[1]),
                "active_leases_count": 1 if is_currently_locked else 0,
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
