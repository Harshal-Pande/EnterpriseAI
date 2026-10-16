"""Order Processing Queue Runner.

Autonomous sequential execution service for orders in the processing queue:
- Enforces strict sequential order execution (one order at a time).
- Atomic claim pattern with `FOR UPDATE SKIP LOCKED`.
- Distributed lease locking via PostgreSQL `scheduler_state` (`order-queue-runner`).
- Configurable interval delay (default 300s, fast in test environment).
- Automatic queue replenishment (maintains 100 queued items if enabled).
- Integrates with GovernedOrchestrator pipeline:
  - Clean runs -> order status COMPLETED, queue status COMPLETED.
  - Policy rejections / approval gates -> order status AT_RISK, queue status WAITING_EXCEPTION,
    and creates record in operational_exceptions.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from app.core.events import EventChannel, EventType, default_event_manager
from app.core.llm_provider import SimulationProvider, get_default_provider
from app.db.database import get_db_connection
from app.models.workflow import WorkflowCreateRequest
from app.orchestration.governed import GovernedOrchestrator, OrchestrationPhase
from app.services.workflow_service import create_workflow

logger = logging.getLogger("enterpriseai.order_runner")

DEFAULT_QUEUE_INTERVAL_SECONDS = 300
DEFAULT_QUEUE_LEASE_SECONDS = 60


def get_queue_interval_seconds() -> int:
    """Retrieve execution interval between sequential order evaluations.
    Default: 300s (5 minutes). Allows >= 1s for tests.
    """
    raw = os.environ.get("ORDER_QUEUE_INTERVAL_SECONDS")
    if raw is not None and raw.strip():
        try:
            val = int(raw.strip())
            if 1 <= val <= 86400:
                return val
        except ValueError:
            pass
    return DEFAULT_QUEUE_INTERVAL_SECONDS


def is_queue_auto_replenish() -> bool:
    """Check whether auto-replenishment is active (default True)."""
    raw = os.environ.get("ORDER_QUEUE_AUTO_REPLENISH", "true").strip().lower()
    return raw in {"true", "1", "yes", "on"}


def is_queue_runner_enabled() -> bool:
    """Check whether the queue runner background loop is enabled."""
    if "pytest" in sys.modules:
        return os.environ.get("ORDER_QUEUE_RUNNER_ENABLED", "false").strip().lower() in {"true", "1", "yes", "on"}
    val = os.environ.get("ORDER_QUEUE_RUNNER_ENABLED", "true").strip().lower()
    return val in {"true", "1", "yes", "on"}


def _log_queue_event(
    cur,
    event_type: str,
    status: str,
    order_id: str,
    scenario_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    now = datetime.now(timezone.utc)
    data = payload or {}
    serialized = json.dumps(data, sort_keys=True, default=str)
    payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    cur.execute(
        """
        INSERT INTO event_log (
            event_id, event_timestamp, event_type, entity_type, entity_id,
            scenario_id, actor_type, actor_id, status, payload_hash, evidence_refs, source_channel
        ) VALUES (
            gen_random_uuid(), %s, %s, 'ORDER', %s,
            %s, 'SYSTEM', 'order-queue-runner', %s, %s, %s, 'QUEUE_RUNNER'
        );
        """,
        (
            now,
            event_type,
            order_id,
            scenario_id,
            status,
            payload_hash,
            serialized,
        ),
    )


def replenish_one_order(conn) -> str:
    """Generate and insert 1 synthetic pending order to replenish the queue.
    
    Preserves variability across customers, entities, products, and priorities,
    including the 33% multi-line distribution pattern.
    Appends order at max(queue_position) + 1.
    """
    with conn.cursor() as cur:
        # Determine next order integer sequence
        cur.execute(
            """
            SELECT COALESCE(MAX(CAST(SUBSTRING(order_id FROM 5) AS INTEGER)), 1241)
            FROM orders
            WHERE order_id ~ '^ORD-[0-9]+$';
            """
        )
        row = cur.fetchone()
        next_num = (row[0] if row and row[0] is not None else 1241) + 1
        new_order_id = f"ORD-{next_num}"

        # Determine next queue position
        cur.execute("SELECT COALESCE(MAX(queue_position), 0) + 1 FROM order_processing_queue;")
        q_row = cur.fetchone()
        next_pos = int(q_row[0]) if q_row and q_row[0] is not None else 1

        customers = [
            "Tata Motors Commercial", "Mahindra & Mahindra Automotive", "Maruti Suzuki India",
            "Larsen & Toubro Heavy Eng", "Adani Ports & SEZ", "Jindal Steel & Power",
            "Steel Authority of India Ltd", "Tata Steel BSL Fabricators", "Bharat Forge Precision",
            "Ashok Leyland Fleet", "BHEL Power Equipment", "Siemens Energy India",
            "Thermax Industrial Boilers", "Alstom Transport India", "Hyundai Motor India",
            "JSW Infrastructure Projects", "Kirloskar Oil Engines", "Sundram Fasteners",
            "Godrej Aerospace Division", "Caterpillar India Mining",
        ]
        entities = ["EAS-EAST", "EAS-WEST", "EAS-PORT", "EAS-HQ"]
        products = ["PRD-HRC", "PRD-CRC", "PRD-REB", "PRD-PLT"]

        customer_ref = customers[next_num % len(customers)]
        entity_id = entities[next_num % len(entities)]

        priorities = ["MEDIUM", "HIGH", "LOW", "CRITICAL"]
        priority = priorities[next_num % 4]

        # Multi-line: ~33% have 2 lines
        has_two_lines = (next_num % 3 == 0)

        prod1_id = products[next_num % len(products)]
        qty1 = float(20 + (next_num * 7 % 90))
        price1 = float(42000.0 + (next_num * 250 % 8000))
        lines_data = [
            (f"OL-{new_order_id}-01", prod1_id, qty1, price1, "MT", qty1 * price1)
        ]

        if has_two_lines:
            prod2_id = products[(next_num + 1) % len(products)]
            qty2 = float(15 + (next_num * 5 % 50))
            price2 = float(44000.0 + (next_num * 350 % 6000))
            lines_data.append(
                (f"OL-{new_order_id}-02", prod2_id, qty2, price2, "MT", qty2 * price2)
            )

        subtotal = sum(l[5] for l in lines_data)
        tax_amount = round(subtotal * 0.18, 2)
        total_amount = round(subtotal + tax_amount, 2)

        now = datetime.now(timezone.utc)
        delivery_date = now + timedelta(days=14)

        # Insert orders record
        cur.execute(
            """
            INSERT INTO orders (
                order_id, customer_ref, entity_id, status, priority,
                currency, external_reference,
                required_delivery_at, created_at, updated_at
            ) VALUES (
                %s, %s, %s, 'OPEN', %s,
                'INR', %s,
                %s, %s, %s
            );
            """,
            (
                new_order_id,
                customer_ref,
                entity_id,
                priority,
                f"REPL-{new_order_id}",
                delivery_date,
                now,
                now,
            ),
        )

        # Insert order_lines
        for line in lines_data:
            cur.execute(
                """
                INSERT INTO order_lines (
                    order_line_id, order_id, product_id,
                    requested_qty, unit_price_inr, uom, created_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s, %s
                );
                """,
                (line[0], new_order_id, line[1], line[2], line[3], line[4], now),
            )

        # Insert queue item
        cur.execute(
            """
            INSERT INTO order_processing_queue (
                queue_id, order_id, queue_position, status,
                enqueued_at, origin, metadata
            ) VALUES (
                gen_random_uuid(), %s, %s, 'QUEUED',
                %s, 'REPLENISHMENT', %s
            );
            """,
            (
                new_order_id,
                next_pos,
                now,
                json.dumps({"replenished_at": now.isoformat(), "total_amount": total_amount}),
            ),
        )

        # Audit event
        _log_queue_event(
            cur,
            event_type="ORDER_REPLENISHED",
            status="SUCCEEDED",
            order_id=new_order_id,
            payload={
                "order_id": new_order_id,
                "queue_position": next_pos,
                "origin": "REPLENISHMENT",
                "total_amount": total_amount,
            },
        )

    return new_order_id


class OrderQueueRunner:
    """Manages sequential execution and lifecycle of the order processing queue."""

    def __init__(self, scheduler_name: str = "order-queue-runner", worker_id: Optional[str] = None):
        self.scheduler_name = scheduler_name
        self.worker_id = worker_id or f"order-runner-{uuid.uuid4().hex[:8]}"
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_skip_reason: Optional[str] = None

    def acquire_lease(self, conn, lease_seconds: int = DEFAULT_QUEUE_LEASE_SECONDS) -> Tuple[bool, Optional[int]]:
        """Acquire distributed lease lock in scheduler_state."""
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
        order_id: Optional[str] = None,
        next_interval: Optional[int] = None,
        skip_reason: Optional[str] = None,
    ) -> None:
        """Release lease lock and update execution timestamps."""
        now = datetime.now(timezone.utc)
        interval = next_interval or get_queue_interval_seconds()
        self._last_skip_reason = skip_reason
        sql = """
            UPDATE scheduler_state
            SET
                locked_by = NULL,
                lease_expires_at = NULL,
                last_scheduled_at = %s,
                next_scheduled_at = %s + (%s || ' seconds')::interval,
                last_status = %s,
                total_runs = total_runs + 1,
                consecutive_failures = CASE WHEN %s = 'FAILED' THEN consecutive_failures + 1 ELSE 0 END,
                updated_at = %s
            WHERE scheduler_name = %s AND (locked_by = %s OR locked_by IS NULL);
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    now,
                    now,
                    str(interval),
                    outcome_status,
                    outcome_status,
                    now,
                    self.scheduler_name,
                    self.worker_id,
                ),
            )
            conn.commit()

    def renew_lease(self, conn, lease_seconds: int = DEFAULT_QUEUE_LEASE_SECONDS) -> bool:
        """Heartbeat renewal of held lease lock."""
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
            cur.execute(sql, (now, str(lease_seconds), now, self.scheduler_name, self.worker_id))
            row = cur.fetchone()
            if row:
                conn.commit()
                return True
            conn.rollback()
            return False

    def claim_next_order(self, conn) -> Optional[Tuple[uuid.UUID, str, int]]:
        """Atomically claim the next eligible QUEUED order with SKIP LOCKED.
        Transitions queue record to PROCESSING and order record to IN_PROGRESS.
        """
        claim_sql = """
            SELECT queue_id, order_id, queue_position
            FROM order_processing_queue
            WHERE status = 'QUEUED'
            ORDER BY queue_position ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED;
        """
        now = datetime.now(timezone.utc)
        with conn.cursor() as cur:
            cur.execute(claim_sql)
            row = cur.fetchone()
            if not row:
                return None

            queue_id, order_id, queue_pos = row[0], row[1], row[2]

            cur.execute(
                """
                UPDATE order_processing_queue
                SET status = 'PROCESSING', claimed_at = %s, attempt_count = attempt_count + 1
                WHERE queue_id = %s;
                """,
                (now, str(queue_id)),
            )

            cur.execute(
                """
                UPDATE orders
                SET status = 'IN_PROGRESS', updated_at = %s
                WHERE order_id = %s;
                """,
                (now, order_id),
            )

            conn.commit()
            return queue_id, order_id, queue_pos

    def process_next_order(
        self,
        conn,
        force: bool = False,
        actor_id: Optional[str] = None,
        llm_provider: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Atomically claim and process exactly one order from the queue.
        
        Strict sequential processing:
        - Locks order-queue-runner lease in scheduler_state.
        - Claims lowest queue_position order in QUEUED status.
        - Auto-replenishes 1 order if enabled.
        - Executes via GovernedOrchestrator pipeline.
        - Transitions to COMPLETED or WAITING_EXCEPTION (with operational_exceptions record).
        """
        lease_sec = DEFAULT_QUEUE_LEASE_SECONDS
        acquired, db_interval = self.acquire_lease(conn, lease_seconds=lease_sec)
        effective_interval = db_interval or get_queue_interval_seconds()

        if not acquired and not force:
            logger.info("Order queue runner lease held or disabled; skipping step.")
            self._last_skip_reason = "LEASE_HELD_OR_PAUSED"
            return {
                "executed": False,
                "status": "SKIPPED",
                "reason": "LEASE_HELD_OR_PAUSED",
                "worker_id": self.worker_id,
            }

        replenished_id: Optional[str] = None
        try:
            # 1. Claim next order atomically
            claim_result = self.claim_next_order(conn)
            if not claim_result:
                self.release_lease(
                    conn,
                    outcome_status="IDLE",
                    next_interval=effective_interval,
                    skip_reason="NO_QUEUED_ORDERS",
                )
                return {
                    "executed": False,
                    "status": "IDLE",
                    "reason": "NO_QUEUED_ORDERS",
                    "worker_id": self.worker_id,
                }

            queue_id, order_id, queue_pos = claim_result

            # 2. Auto-replenish queue tail if enabled
            if is_queue_auto_replenish():
                try:
                    replenished_id = replenish_one_order(conn)
                    conn.commit()
                except Exception as rep_err:
                    logger.warning("Replenishment error during order claim: %s", rep_err)
                    conn.rollback()

            # 3. Locate or create workflow instance for governed pipeline
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT scenario_id, status FROM scenario_instances
                    WHERE linked_order_id = %s
                    ORDER BY created_at DESC LIMIT 1;
                    """,
                    (order_id,),
                )
                s_row = cur.fetchone()

            if s_row:
                scenario_id = str(s_row[0])
                workflow_id = scenario_id
            else:
                # Create standard operational workflow instance (TPL-010 Normal Operations)
                create_req = WorkflowCreateRequest(
                    scenario_template_id="TPL-010",
                    linked_order_id=order_id,
                    severity="LOW",
                    execute_immediately=False,
                    data_mode="SYNTHETIC",
                    idempotency_key=f"QUEUE-RUN-{order_id}-{uuid.uuid4().hex[:6]}",
                )
                instance = create_workflow(conn, create_req)
                scenario_id = str(instance.scenario_id)
                workflow_id = str(instance.workflow_id)

            # 4. Execute governed multi-agent orchestration
            # Use provided llm_provider, default provider, or SimulationProvider if live is unconfigured
            provider = llm_provider or get_default_provider()
            orchestrator = GovernedOrchestrator(llm_provider=provider)

            result = orchestrator.execute(
                workflow_id=workflow_id,
                order_id=order_id,
                conn=conn,
                scenario_id=scenario_id,
            )

            now = datetime.now(timezone.utc)
            final_status: str
            exception_id: Optional[uuid.UUID] = None

            # 5. Determine outcome
            is_policy_rejected = result.governance.get("policy_rejected", False)
            is_awaiting_approval = result.status in ("AWAITING_APPROVAL", "WAITING_APPROVAL")
            is_clean_completion = result.status == "COMPLETED" and not is_policy_rejected

            with conn.cursor() as cur:
                if is_clean_completion:
                    # Clean run
                    cur.execute(
                        """
                        UPDATE order_processing_queue
                        SET status = 'COMPLETED', completed_at = %s, last_error = NULL
                        WHERE queue_id = %s;
                        """,
                        (now, str(queue_id)),
                    )
                    cur.execute(
                        """
                        UPDATE orders
                        SET status = 'COMPLETED', updated_at = %s
                        WHERE order_id = %s;
                        """,
                        (now, order_id),
                    )
                    final_status = "COMPLETED"

                    # Log completion event
                    _log_queue_event(
                        cur,
                        event_type="ORDER_COMPLETED",
                        status="COMPLETED",
                        order_id=order_id,
                        scenario_id=scenario_id,
                        payload={"order_id": order_id, "queue_id": str(queue_id), "status": "COMPLETED"},
                    )

                else:
                    # Exception or policy hold encountered
                    final_status = "WAITING_EXCEPTION"
                    exception_id = uuid.uuid4()
                    err_msg = result.error or "Governance policy approval gate reached."
                    cause = err_msg
                    severity = "CRITICAL" if is_policy_rejected else "HIGH"

                    err_lower = err_msg.lower()
                    if "budget" in err_lower or "financial" in err_lower or "limit" in err_lower or "commitment" in err_lower:
                        exc_type = "BUDGET_BREACH"
                    elif "stock" in err_lower or "inventory" in err_lower or "shortage" in err_lower:
                        exc_type = "STOCK_SHORTFALL"
                    elif "supplier" in err_lower:
                        exc_type = "SUPPLIER_UNAVAILABLE"
                    elif "delivery" in err_lower or "delay" in err_lower:
                        exc_type = "DELIVERY_DELAY"
                    elif "quality" in err_lower or "safety" in err_lower:
                        exc_type = "QUALITY_SAFETY"
                    elif "agent" in err_lower:
                        exc_type = "AGENT_FAILURE"
                    else:
                        exc_type = "POLICY_VIOLATION"

                    rec_action = {
                        "action_type": "EXPEDITE_PO",
                        "summary": "Operator action required to resolve policy exception.",
                        "recommended_by": "GovernedOrchestrator",
                    }
                    prop_action = {
                        "action_type": "RESOLVE_DISRUPTION",
                        "order_id": order_id,
                        "notes": err_msg,
                    }

                    # Insert operational exception record
                    cur.execute(
                        """
                        INSERT INTO operational_exceptions (
                            exception_id, order_id, scenario_id, workflow_run_id,
                            severity, exception_type, cause, owner_role, status,
                            ai_recommendation, proposed_action, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, 'OPERATOR', 'OPEN',
                            %s, %s, %s, %s
                        );
                        """,
                        (
                            str(exception_id),
                            order_id,
                            str(scenario_id),
                            str(workflow_id),
                            severity,
                            exc_type,
                            cause,
                            json.dumps(rec_action),
                            json.dumps(prop_action),
                            now,
                            now,
                        ),
                    )

                    # Update queue item to WAITING_EXCEPTION
                    cur.execute(
                        """
                        UPDATE order_processing_queue
                        SET status = 'WAITING_EXCEPTION', exception_id = %s, last_error = %s
                        WHERE queue_id = %s;
                        """,
                        (str(exception_id), err_msg[:500], str(queue_id)),
                    )

                    # Update order to AT_RISK
                    cur.execute(
                        """
                        UPDATE orders
                        SET status = 'AT_RISK', updated_at = %s
                        WHERE order_id = %s;
                        """,
                        (now, order_id),
                    )

                    # Log exception event
                    _log_queue_event(
                        cur,
                        event_type="ORDER_EXCEPTION_RAISED",
                        status="WAITING_EXCEPTION",
                        order_id=order_id,
                        scenario_id=scenario_id,
                        payload={
                            "order_id": order_id,
                            "queue_id": str(queue_id),
                            "exception_id": str(exception_id),
                            "cause": cause,
                        },
                    )

                conn.commit()

            # 6. Release lease and schedule next run
            self.release_lease(
                conn,
                outcome_status=final_status,
                order_id=order_id,
                next_interval=effective_interval,
            )

            # Publish WebSocket event
            try:
                default_event_manager.publish(
                    EventChannel.ORCHESTRATION,
                    EventType.WORKFLOW_COMPLETED if final_status == "COMPLETED" else EventType.APPROVAL_REQUIRED,
                    {
                        "order_id": order_id,
                        "queue_id": str(queue_id),
                        "status": final_status,
                        "exception_id": str(exception_id) if exception_id else None,
                        "replenished_order_id": replenished_id,
                    },
                )
            except Exception:
                pass

            return {
                "executed": True,
                "status": final_status,
                "order_id": order_id,
                "queue_id": str(queue_id),
                "scenario_id": scenario_id,
                "exception_id": str(exception_id) if exception_id else None,
                "replenished_order_id": replenished_id,
                "error": result.error if final_status == "WAITING_EXCEPTION" else None,
                "worker_id": self.worker_id,
            }

        except Exception as exc:
            logger.error("Unhandled error in order queue runner execution: %s", exc)
            conn.rollback()
            try:
                self.release_lease(
                    conn,
                    outcome_status="FAILED",
                    next_interval=effective_interval,
                    skip_reason=str(exc),
                )
            except Exception:
                pass
            return {
                "executed": False,
                "status": "FAILED",
                "error": str(exc),
                "worker_id": self.worker_id,
            }

    def pause(self, conn) -> bool:
        """Pause the queue runner."""
        now = datetime.now(timezone.utc)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduler_state
                SET enabled = FALSE, last_status = 'PAUSED', updated_at = %s
                WHERE scheduler_name = %s;
                """,
                (now, self.scheduler_name),
            )
            conn.commit()
        return True

    def resume(self, conn) -> bool:
        """Resume the queue runner."""
        now = datetime.now(timezone.utc)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduler_state
                SET enabled = TRUE, last_status = 'RUNNING', updated_at = %s
                WHERE scheduler_name = %s;
                """,
                (now, self.scheduler_name),
            )
            conn.commit()
        return True

    def get_status(self, conn=None) -> Dict[str, Any]:
        """Fetch current runner state, counts, next run time, and locks."""
        if conn is None:
            with get_db_connection() as c:
                return self.get_status(c)

        counts_sql = """
            SELECT
                COUNT(*) FILTER (WHERE status = 'QUEUED') AS queued_count,
                COUNT(*) FILTER (WHERE status = 'PROCESSING') AS processing_count,
                COUNT(*) FILTER (WHERE status = 'WAITING_EXCEPTION') AS waiting_exception_count,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed_count,
                COUNT(*) AS total_tracked
            FROM order_processing_queue;
        """
        sched_sql = """
            SELECT
                enabled,
                interval_seconds,
                last_status,
                last_scheduled_at,
                next_scheduled_at,
                locked_by,
                lease_expires_at,
                total_runs,
                consecutive_failures
            FROM scheduler_state
            WHERE scheduler_name = %s;
        """
        with conn.cursor() as cur:
            cur.execute(counts_sql)
            c_row = cur.fetchone()
            cur.execute(sched_sql, (self.scheduler_name,))
            s_row = cur.fetchone()

        now = datetime.now(timezone.utc)
        enabled = s_row[0] if s_row else True
        interval = s_row[1] if s_row else DEFAULT_QUEUE_INTERVAL_SECONDS
        last_status = s_row[2] or ("RUNNING" if enabled else "PAUSED")
        last_run = s_row[3]
        next_run = s_row[4]
        locked_by = s_row[5]
        lease_expires = s_row[6]
        is_locked = bool(locked_by and lease_expires and lease_expires > now)

        if last_run and (not next_run or next_run < now) and enabled:
            next_run = last_run + timedelta(seconds=interval)

        return {
            "scheduler_name": self.scheduler_name,
            "runner_enabled": enabled,
            "runner_status": "PAUSED" if not enabled else ("PROCESSING" if is_locked else last_status),
            "runner_interval_seconds": interval,
            "configured_interval_seconds": interval,
            "last_scheduled_at": last_run.isoformat() if last_run else None,
            "next_eligible_run_time": next_run.isoformat() if next_run else None,
            "next_scheduled_at": next_run.isoformat() if next_run else None,
            "is_locked": is_locked,
            "locked_by": locked_by if is_locked else None,
            "total_queued": int(c_row[0]) if c_row else 0,
            "processing_count": int(c_row[1]) if c_row else 0,
            "waiting_exception_count": int(c_row[2]) if c_row else 0,
            "completed_count": int(c_row[3]) if c_row else 0,
            "total_orders_tracked": int(c_row[4]) if c_row else 0,
            "background_worker_active": self._running,
            "total_runs": int(s_row[7]) if s_row and s_row[7] else 0,
            "consecutive_failures": int(s_row[8]) if s_row and s_row[8] else 0,
        }

    async def _loop(self):
        """Asynchronous background loop honoring backend delay."""
        interval = get_queue_interval_seconds()
        logger.info("Starting background order queue runner loop with %ds interval", interval)
        self._running = True
        try:
            while self._running:
                await asyncio.sleep(interval)
                if not self._running:
                    break
                try:
                    with get_db_connection() as conn:
                        self.process_next_order(conn)
                except Exception as exc:
                    logger.warning("Order queue runner loop encountered error: %s", exc)
        except asyncio.CancelledError:
            logger.info("Order queue runner loop cancelled cleanly.")
        finally:
            self._running = False

    def start(self):
        """Start the background task loop in current asyncio event loop."""
        if not is_queue_runner_enabled():
            logger.info("Order queue runner disabled via ORDER_QUEUE_RUNNER_ENABLED=false; loop not started.")
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


# Singleton instance for application runtime
default_order_queue_runner = OrderQueueRunner()
