"""WebSocket Real-Time API Endpoint (Phase 6).

Provides:
- Authenticated WebSocket endpoint /api/ws and /api/ws/events
- Safe connection lifecycle: authentication, heartbeat, subscriptions, and disconnect
- Replay and recovery for disconnected or missed events
- Observability status endpoint GET /api/ws/status
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.core.events import (
    EventChannel,
    EventType,
    default_event_manager,
)
from app.core.security import (
    AuthUser,
    UserRole,
    authenticate_ws_credentials,
    require_role,
)
from app.db.database import get_db

logger = logging.getLogger("enterpriseai.api.ws")

router = APIRouter()


@router.websocket("/ws")
@router.websocket("/ws/events")
async def websocket_event_stream(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None, description="API Key for authentication"),
    token: Optional[str] = Query(None, description="Bearer token fallback"),
):
    """Real-time WebSocket event streaming endpoint.

    Workflow:
    1. Authenticate client via server-side credential registry.
    2. Enforce role-based access control and maximum connection limits.
    3. Accept connection and confirm session establishment.
    4. Handle inbound heartbeats (PING/PONG), channel subscriptions, and replay requests.
    5. Clean up connection context on disconnect.
    """
    # 1. Authenticate credentials
    try:
        user = authenticate_ws_credentials(api_key=api_key, token=token)
    except HTTPException as exc:
        logger.warning("WebSocket authentication failed: %s", exc.detail)
        await websocket.close(code=1008, reason=str(exc.detail)[:120])
        return
    except Exception as exc:
        logger.error("Unexpected WebSocket authentication error: %s", exc)
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # 2. Accept and register connection
    await websocket.accept()
    try:
        ctx = await default_event_manager.connect(websocket, user)
    except RuntimeError:
        # Max capacity reached — already closed in connect()
        return

    # 3. Transmit connection confirmation
    await websocket.send_text(
        json.dumps({
            "event_type": "CONNECTED",
            "timestamp": ctx.connected_at,
            "payload": {
                "user_id": user.user_id,
                "role": user.role.value,
                "subscriptions": list(ctx.subscribed_channels),
                "approval_domains": user.approval_domains,
            },
        })
    )

    # 4. Message processing loop
    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({
                        "event_type": EventType.ERROR.value,
                        "payload": {"message": "Malformed message: invalid JSON syntax"},
                    })
                )
                continue

            action = str(data.get("action", "")).lower()

            if action == "ping":
                await websocket.send_text(
                    json.dumps({
                        "event_type": EventType.PONG.value,
                        "timestamp": data.get("timestamp"),
                        "payload": {"status": "healthy"},
                    })
                )

            elif action == "subscribe":
                channels = data.get("channels", ["all"])
                if isinstance(channels, str):
                    channels = [channels]
                entity_id = data.get("entity_id")
                sub_res = await default_event_manager.update_subscriptions(
                    websocket,
                    channels=channels,
                    entity_id=entity_id,
                )
                await websocket.send_text(
                    json.dumps({
                        "event_type": EventType.SUBSCRIPTION_CONFIRMED.value,
                        "payload": sub_res,
                    })
                )

            elif action == "replay":
                since_timestamp = data.get("since_timestamp")
                last_event_id = data.get("last_event_id")
                limit = data.get("limit", 50)

                # Acquire database connection for replay query
                conn = None
                try:
                    conn = next(get_db())
                    await default_event_manager.replay_from_db(
                        websocket=websocket,
                        user=user,
                        conn=conn,
                        since_timestamp=since_timestamp,
                        last_event_id=last_event_id,
                        limit=limit,
                    )
                except Exception as exc:
                    logger.error("Error during event replay: %s", exc)
                    await websocket.send_text(
                        json.dumps({
                            "event_type": EventType.ERROR.value,
                            "payload": {"message": "Failed to replay events from database"},
                        })
                    )
                finally:
                    if conn:
                        try:
                            conn.close()
                        except Exception:
                            pass

            else:
                await websocket.send_text(
                    json.dumps({
                        "event_type": EventType.ERROR.value,
                        "payload": {
                            "message": f"Unknown action: '{action}'. Supported actions: ping, subscribe, replay.",
                        },
                    })
                )

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed by client: user=%s", user.user_id)
    except Exception as exc:
        logger.error("Unexpected error in WebSocket loop: %s", exc)
    finally:
        await default_event_manager.disconnect(websocket)


@router.get("/ws/status", tags=["websocket"])
def get_websocket_status(
    current_user: AuthUser = Depends(require_role(UserRole.VIEWER)),
):
    """Retrieve operational telemetry and health status for WebSocket event broker."""
    return {
        "status": "operational",
        "active_connections": default_event_manager.connection_count,
        "max_connections": 100,
        "supported_channels": [ch.value for ch in EventChannel],
        "authenticated_user": current_user.user_id,
        "role": current_user.role.value,
    }
