"""Real-Time Event Bus and WebSocket Connection Manager (Phase 6).

Provides:
- Strongly-typed WebSocket message framing and event schemas
- Role-based channel subscriptions and entity-level event filtering
- Asynchronous and synchronous event publishing from operational lifecycles
- Reconnection event replay from PostgreSQL event_log
- Connection limits, subscription quotas, and safe client lifecycle management
- Sanitized event broadcasting preventing sensitive data / credential leakage
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.core.security import AuthUser, UserRole

logger = logging.getLogger("enterpriseai.events")

MAX_WEBSOCKET_CONNECTIONS = 100
MAX_SUBSCRIPTIONS_PER_CLIENT = 25
DEFAULT_REPLAY_LIMIT = 50
MAX_REPLAY_LIMIT = 200


class EventChannel(str, Enum):
    WORKFLOWS = "workflows"
    ORCHESTRATION = "orchestration"
    APPROVALS = "approvals"
    ACTIONS = "actions"
    SCHEDULER = "scheduler"
    AUDIT = "audit"
    ALL = "all"


class EventType(str, Enum):
    # Workflow transitions
    WORKFLOW_CREATED = "WORKFLOW_CREATED"
    WORKFLOW_STATUS_CHANGED = "WORKFLOW_STATUS_CHANGED"

    # Orchestration
    ORCHESTRATION_STARTED = "ORCHESTRATION_STARTED"
    AGENT_STEP_COMPLETED = "AGENT_STEP_COMPLETED"
    ORCHESTRATION_COMPLETED = "ORCHESTRATION_COMPLETED"
    ORCHESTRATION_FAILED = "ORCHESTRATION_FAILED"

    # Policy and Approvals
    POLICY_EVALUATED = "POLICY_EVALUATED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_DECIDED = "APPROVAL_DECIDED"

    # Actions
    ACTION_PROPOSED = "ACTION_PROPOSED"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_FAILED = "ACTION_FAILED"

    # Scheduler
    SCHEDULER_CYCLE_STARTED = "SCHEDULER_CYCLE_STARTED"
    SCENARIO_GENERATED = "SCENARIO_GENERATED"
    SCENARIO_SKIPPED = "SCENARIO_SKIPPED"

    # Protocol
    PING = "PING"
    PONG = "PONG"
    SUBSCRIPTION_CONFIRMED = "SUBSCRIPTION_CONFIRMED"
    REPLAY_STARTED = "REPLAY_STARTED"
    REPLAY_EVENT = "REPLAY_EVENT"
    REPLAY_COMPLETE = "REPLAY_COMPLETE"
    ERROR = "ERROR"


class WSEvent(BaseModel):
    """Outbound real-time event message."""

    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:12].upper()}")
    event_type: str
    channel: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    scenario_id: Optional[str] = None
    workflow_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_replay: bool = False


class InboundMessage(BaseModel):
    """Inbound client command."""

    action: str
    channels: Optional[List[str]] = None
    entity_id: Optional[str] = None
    since_timestamp: Optional[str] = None
    last_event_id: Optional[str] = None
    limit: Optional[int] = None
    timestamp: Optional[str] = None


class ConnectionContext:
    """Session context for an authenticated WebSocket client."""

    def __init__(self, websocket: WebSocket, user: AuthUser, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.websocket = websocket
        self.user = user
        self.loop = loop
        self.subscribed_channels: Set[str] = {EventChannel.ALL.value}
        self.entity_filter: Optional[str] = None
        self.connected_at = datetime.now(timezone.utc).isoformat()
        self.message_count = 0


class EventManager:
    """Thread-safe WebSocket Connection and Broadcast Broker."""

    def __init__(self):
        self._connections: Dict[WebSocket, ConnectionContext] = {}
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket, user: AuthUser) -> ConnectionContext:
        """Register a new authenticated WebSocket connection."""
        try:
            current_loop = asyncio.get_running_loop()
            self._loop = current_loop
        except RuntimeError:
            current_loop = self._loop

        async with self._lock:
            if len(self._connections) >= MAX_WEBSOCKET_CONNECTIONS:
                logger.warning(
                    "WebSocket connection rejected: server capacity limit of %d reached",
                    MAX_WEBSOCKET_CONNECTIONS,
                )
                await websocket.close(code=1008, reason="Server connection capacity reached")
                raise RuntimeError("Max WebSocket connections reached")

            ctx = ConnectionContext(websocket, user, loop=current_loop)
            self._connections[websocket] = ctx
            logger.info(
                "WebSocket client connected: user_id=%s, role=%s (active: %d)",
                user.user_id,
                user.role.value,
                len(self._connections),
            )
            return ctx

    async def disconnect(self, websocket: WebSocket):
        """Unregister a disconnected WebSocket client."""
        async with self._lock:
            ctx = self._connections.pop(websocket, None)
            if ctx:
                logger.info(
                    "WebSocket client disconnected: user_id=%s (remaining: %d)",
                    ctx.user.user_id,
                    len(self._connections),
                )

    async def update_subscriptions(
        self,
        websocket: WebSocket,
        channels: List[str],
        entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update subscription channels and entity filter for a connection."""
        async with self._lock:
            ctx = self._connections.get(websocket)
            if not ctx:
                return {"status": "error", "message": "Connection not found"}

            valid_channels: Set[str] = set()
            for ch in channels:
                clean = ch.strip().lower()
                try:
                    valid_channels.add(EventChannel(clean).value)
                except ValueError:
                    if clean == "all":
                        valid_channels.add(EventChannel.ALL.value)

            if len(valid_channels) > MAX_SUBSCRIPTIONS_PER_CLIENT:
                return {
                    "status": "error",
                    "message": f"Cannot subscribe to more than {MAX_SUBSCRIPTIONS_PER_CLIENT} channels",
                }

            ctx.subscribed_channels = valid_channels or {EventChannel.ALL.value}
            ctx.entity_filter = entity_id.strip() if entity_id else None

            return {
                "status": "success",
                "channels": list(ctx.subscribed_channels),
                "entity_filter": ctx.entity_filter,
            }

    async def broadcast(self, event: WSEvent):
        """Broadcast an event to all interested, authorized subscribers."""
        async with self._lock:
            connections = list(self._connections.values())

        if not connections:
            return

        dead_sockets: List[WebSocket] = []
        event_dict = event.model_dump()

        for ctx in connections:
            try:
                # 1. Channel filter check
                subbed = ctx.subscribed_channels
                if EventChannel.ALL.value not in subbed and event.channel not in subbed:
                    continue

                # 2. Entity filter check
                if ctx.entity_filter:
                    if (
                        ctx.entity_filter != event.entity_id
                        and ctx.entity_filter != event.scenario_id
                        and ctx.entity_filter != event.workflow_id
                    ):
                        continue

                # 3. Role-based payload filtering
                filtered_event = self._filter_event_for_user(event_dict, ctx.user)

                # 4. Transmit
                await ctx.websocket.send_text(json.dumps(filtered_event))
            except (WebSocketDisconnect, RuntimeError, Exception) as exc:
                logger.debug("Failed sending event to client: %s", exc)
                dead_sockets.append(ctx.websocket)

        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    self._connections.pop(ws, None)

    def _filter_event_for_user(self, event_dict: Dict[str, Any], user: AuthUser) -> Dict[str, Any]:
        """Apply least-privilege security filters to outbound event payloads."""
        # Admin and Operators see full payload
        if user.role in {UserRole.ADMIN, UserRole.OPERATOR, UserRole.FINANCE_APPROVER, UserRole.SUPPLY_CHAIN_APPROVER}:
            return event_dict

        # Viewers: Mask raw credentials, database connection strings, or sensitive internal tokens if present
        payload = dict(event_dict.get("payload", {}))
        sensitive_keys = {"token", "secret", "password", "api_key", "connection_string", "private_key"}
        sanitized_payload = {
            k: ("[REDACTED]" if k.lower() in sensitive_keys else v)
            for k, v in payload.items()
        }
        res = dict(event_dict)
        res["payload"] = sanitized_payload
        return res

    def publish(
        self,
        event_type: str,
        channel: str,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        scenario_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        wait: bool = False,
    ):
        """Synchronously or asynchronously publish an event to the global event bus.

        Safely works from both async FastAPI routes and synchronous services/threads.
        """
        event = WSEvent(
            event_type=event_type,
            channel=channel,
            entity_id=entity_id,
            entity_type=entity_type,
            scenario_id=scenario_id,
            workflow_id=workflow_id,
            payload=payload or {},
        )

        running_loop = None
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        target_loop = running_loop or self._loop
        if not target_loop or not target_loop.is_running():
            for ctx in self._connections.values():
                if ctx.loop and ctx.loop.is_running():
                    target_loop = ctx.loop
                    self._loop = target_loop
                    break

        if running_loop and running_loop.is_running():
            asyncio.create_task(self.broadcast(event))
        elif target_loop and target_loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self.broadcast(event), target_loop)
            if wait:
                try:
                    fut.result(timeout=2.0)
                except Exception as exc:
                    logger.warning("Error waiting for broadcast completion: %s", exc)
        else:
            logger.debug("No active event loop found; event published to log only: %s", event_type)

    async def replay_from_db(
        self,
        websocket: WebSocket,
        user: AuthUser,
        conn,
        since_timestamp: Optional[str] = None,
        last_event_id: Optional[str] = None,
        limit: int = DEFAULT_REPLAY_LIMIT,
    ):
        """Replay recent historical events from event_log to catch up a reconnected client."""
        effective_limit = min(max(1, limit), MAX_REPLAY_LIMIT)

        clauses: List[str] = []
        params: List[Any] = []

        if since_timestamp:
            clauses.append("event_timestamp > %s")
            params.append(since_timestamp)

        if last_event_id:
            try:
                uuid.UUID(last_event_id)
                clauses.append("event_timestamp > (SELECT event_timestamp FROM event_log WHERE event_id = %s)")
                params.append(last_event_id)
            except ValueError:
                pass

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT
                event_id, event_timestamp, event_type, entity_type, entity_id,
                scenario_id, workflow_run_id, status, reason_code, evidence_refs, source_channel
            FROM event_log
            {where_sql}
            ORDER BY event_timestamp ASC
            LIMIT %s;
        """
        params.append(effective_limit)

        await websocket.send_text(
            json.dumps({
                "event_type": EventType.REPLAY_STARTED.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"requested_limit": effective_limit},
            })
        )

        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

            for row in rows:
                (
                    e_id,
                    e_time,
                    e_type,
                    ent_type,
                    ent_id,
                    scen_id,
                    wf_id,
                    status_val,
                    reason,
                    evidence,
                    src_ch,
                ) = row

                payload = {
                    "status": status_val,
                    "reason_code": reason,
                    "evidence_refs": evidence if isinstance(evidence, (list, dict)) else [],
                    "source_channel": src_ch,
                }

                channel = EventChannel.AUDIT.value
                if "WORKFLOW" in e_type:
                    channel = EventChannel.WORKFLOWS.value
                elif "AGENT" in e_type or "ORCHESTRATION" in e_type:
                    channel = EventChannel.ORCHESTRATION.value
                elif "APPROVAL" in e_type:
                    channel = EventChannel.APPROVALS.value
                elif "ACTION" in e_type:
                    channel = EventChannel.ACTIONS.value
                elif "SCHEDULER" in e_type or "SCENARIO" in e_type:
                    channel = EventChannel.SCHEDULER.value

                ws_event = WSEvent(
                    event_id=f"EVT-{str(e_id)[:8]}",
                    event_type=e_type,
                    channel=channel,
                    timestamp=e_time.isoformat() if hasattr(e_time, "isoformat") else str(e_time),
                    entity_id=str(ent_id) if ent_id else None,
                    entity_type=ent_type,
                    scenario_id=str(scen_id) if scen_id else None,
                    workflow_id=str(wf_id) if wf_id else None,
                    payload=payload,
                    is_replay=True,
                )
                filtered = self._filter_event_for_user(ws_event.model_dump(), user)
                await websocket.send_text(json.dumps(filtered))

        except Exception as exc:
            logger.error("Failed replaying events from database: %s", exc)

        await websocket.send_text(
            json.dumps({
                "event_type": EventType.REPLAY_COMPLETE.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"status": "complete"},
            })
        )


# Global singleton instance
default_event_manager = EventManager()
