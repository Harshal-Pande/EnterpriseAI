"""Phase 6 Targeted Tests — WebSocket connection lifecycle, subscriptions, replay, and RBAC."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.events import (
    EventChannel,
    EventType,
    WSEvent,
    default_event_manager,
)
from app.core.security import AuthUser, UserRole
from app.main import app

client = TestClient(app)


def test_ws_status_endpoint():
    """Verify GET /api/ws/status returns broker health and capabilities."""
    response = client.get(
        "/api/ws/status",
        headers={"X-API-Key": "dev-viewer-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "active_connections" in data
    assert "supported_channels" in data
    assert "workflows" in data["supported_channels"]
    assert "approvals" in data["supported_channels"]
    assert "actions" in data["supported_channels"]


def test_ws_status_unauthorized_without_credentials_in_prod(monkeypatch):
    """Verify GET /api/ws/status fails closed in production mode without credentials."""
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    response = client.get("/api/ws/status")
    assert response.status_code in (401, 500)


def test_ws_connection_success_with_api_key():
    """Verify WebSocket client connects successfully with valid API key."""
    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws:
        init_frame = ws.receive_json()
        assert init_frame["event_type"] == "CONNECTED"
        assert init_frame["payload"]["role"] == "OPERATOR"
        assert init_frame["payload"]["user_id"] == "operator_user"


def test_ws_connection_rejected_on_invalid_credentials():
    """Verify WebSocket connection is rejected with code 1008 for invalid credentials."""
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws?api_key=invalid-secret-key") as ws:
            ws.receive_json()


def test_ws_ping_pong():
    """Verify PING message receives PONG with preserved timestamp."""
    with client.websocket_connect("/api/ws?api_key=dev-viewer-key") as ws:
        # Initial greeting
        ws.receive_json()

        # Send ping
        ws.send_json({"action": "ping", "timestamp": "2026-10-14T12:00:00Z"})
        resp = ws.receive_json()
        assert resp["event_type"] == "PONG"
        assert resp["timestamp"] == "2026-10-14T12:00:00Z"
        assert resp["payload"]["status"] == "healthy"


def test_ws_channel_subscription():
    """Verify client can update channel subscriptions."""
    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws:
        ws.receive_json()  # greeting

        ws.send_json({
            "action": "subscribe",
            "channels": ["approvals", "actions"],
            "entity_id": "ORD-1042",
        })
        resp = ws.receive_json()
        assert resp["event_type"] == "SUBSCRIPTION_CONFIRMED"
        payload = resp["payload"]
        assert payload["status"] == "success"
        assert set(payload["channels"]) == {"approvals", "actions"}
        assert payload["entity_filter"] == "ORD-1042"


def test_ws_malformed_json_handling():
    """Verify malformed JSON message receives ERROR frame without crashing."""
    with client.websocket_connect("/api/ws?api_key=dev-viewer-key") as ws:
        ws.receive_json()  # greeting

        ws.send_text("this is not json {{{")
        resp = ws.receive_json()
        assert resp["event_type"] == "ERROR"
        assert "Malformed message" in resp["payload"]["message"]


def test_ws_event_broadcast_and_channel_filtering():
    """Verify broadcast delivers to subscribed channels and ignores unsubscribed channels."""
    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws:
        ws.receive_json()  # greeting

        # Subscribe specifically to approvals
        ws.send_json({
            "action": "subscribe",
            "channels": ["approvals"],
        })
        ws.receive_json()  # confirmation

        # Broadcast event on 'scheduler' channel (should be skipped)
        default_event_manager.publish(
            event_type="SCHEDULER_CYCLE_STARTED",
            channel="scheduler",
            payload={"cycle": 1},
            wait=True,
        )

        # Broadcast event on 'approvals' channel (should be received)
        default_event_manager.publish(
            event_type="APPROVAL_REQUESTED",
            channel="approvals",
            entity_id="APP-1234",
            payload={"amount": 75000000},
            wait=True,
        )

        received = ws.receive_json()
        assert received["event_type"] == "APPROVAL_REQUESTED"
        assert received["channel"] == "approvals"
        assert received["entity_id"] == "APP-1234"


def test_ws_entity_filter():
    """Verify entity-level subscription filter delivers only matching events."""
    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws:
        ws.receive_json()  # greeting

        # Subscribe to actions with filter on target entity 'ACT-999'
        ws.send_json({
            "action": "subscribe",
            "channels": ["actions"],
            "entity_id": "ACT-999",
        })
        ws.receive_json()  # confirmation

        # Event for different entity (ACT-000)
        default_event_manager.publish(
            event_type="ACTION_EXECUTED",
            channel="actions",
            entity_id="ACT-000",
            payload={"status": "SUCCEEDED"},
            wait=True,
        )

        # Event for matching entity (ACT-999)
        default_event_manager.publish(
            event_type="ACTION_EXECUTED",
            channel="actions",
            entity_id="ACT-999",
            payload={"status": "SUCCEEDED"},
            wait=True,
        )

        received = ws.receive_json()
        assert received["event_type"] == "ACTION_EXECUTED"
        assert received["entity_id"] == "ACT-999"


def test_ws_viewer_role_payload_masking():
    """Verify unprivileged VIEWER role receives redacted sensitive fields."""
    with client.websocket_connect("/api/ws?api_key=dev-viewer-key") as ws:
        ws.receive_json()  # greeting

        # Broadcast event containing sensitive keys
        default_event_manager.publish(
            event_type="SECRET_EVENT",
            channel="all",
            payload={
                "public_info": "All systems operational",
                "secret": "super_secret_token",
                "api_key": "raw_api_key_value",
            },
            wait=True,
        )

        received = ws.receive_json()
        payload = received["payload"]
        assert payload["public_info"] == "All systems operational"
        assert payload["secret"] == "[REDACTED]"
        assert payload["api_key"] == "[REDACTED]"


def test_ws_replay_flow():
    """Verify client replay request receives REPLAY_STARTED and REPLAY_COMPLETE."""
    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws:
        ws.receive_json()  # greeting

        ws.send_json({
            "action": "replay",
            "limit": 10,
        })

        start_frame = ws.receive_json()
        assert start_frame["event_type"] == "REPLAY_STARTED"

        # Eventually receives REPLAY_COMPLETE (with 0 or more REPLAY_EVENT in between)
        msg = ws.receive_json()
        while msg.get("event_type") != "REPLAY_COMPLETE":
            assert msg.get("is_replay") is True
            msg = ws.receive_json()

        assert msg["event_type"] == "REPLAY_COMPLETE"


def test_ws_ticket_issuance_and_single_use_auth():
    """Verify POST /api/ws/ticket issues a single-use ticket that authenticates and cannot be reused."""
    # 1. Issue ticket for authenticated operator
    response = client.post(
        "/api/ws/ticket",
        headers={"X-API-Key": "dev-operator-key"},
    )
    assert response.status_code == 200
    ticket_data = response.json()
    assert "ticket" in ticket_data
    assert ticket_data["role"] == "OPERATOR"
    ticket = ticket_data["ticket"]

    # 2. First connection with ticket succeeds
    with client.websocket_connect(f"/api/ws?ticket={ticket}") as ws:
        init_frame = ws.receive_json()
        assert init_frame["event_type"] == "CONNECTED"
        assert init_frame["payload"]["role"] == "OPERATOR"

    # 3. Second connection attempt with the SAME ticket is rejected (single use)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/ws?ticket={ticket}") as ws2:
            ws2.receive_json()


def test_ws_ticket_forged_or_invalid_rejected():
    """Verify forged or random ticket is immediately rejected."""
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws?ticket=completely_fake_forged_ticket_123") as ws:
            ws.receive_json()


def test_ws_publish_with_zero_subscribers():
    """Verify publishing when no subscribers are connected does not raise unhandled exceptions."""
    try:
        default_event_manager.publish(
            event_type="UNSUBSCRIBED_EVENT",
            channel="workflows",
            payload={"info": "no listeners"},
            wait=False,
        )
    except Exception as exc:
        pytest.fail(f"Publishing with zero subscribers raised unhandled exception: {exc}")


def test_ws_cross_thread_publishing():
    """Verify events published from background worker threads reach connected clients."""
    import threading

    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws:
        ws.receive_json()  # greeting

        def background_publisher():
            default_event_manager.publish(
                event_type="BACKGROUND_THREAD_EVENT",
                channel="all",
                payload={"thread": "worker-1", "value": 42},
                wait=True,
            )

        thread = threading.Thread(target=background_publisher)
        thread.start()
        thread.join(timeout=3.0)
        assert not thread.is_alive()

        event = ws.receive_json()
        assert event["event_type"] == "BACKGROUND_THREAD_EVENT"
        assert event["payload"]["thread"] == "worker-1"
        assert event["payload"]["value"] == 42


def test_ws_unrelated_connection_isolation_on_disconnect():
    """Verify a closed connection does not affect delivery to other live connections."""
    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws1:
        ws1.receive_json()  # greeting 1

        with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws2:
            ws2.receive_json()  # greeting 2

            # Now ws2 exits this block and closes
        # ws2 is closed, ws1 remains open

        # Publish an event to all
        default_event_manager.publish(
            event_type="ISOLATION_TEST_EVENT",
            channel="all",
            payload={"status": "live"},
            wait=True,
        )

        event = ws1.receive_json()
        assert event["event_type"] == "ISOLATION_TEST_EVENT"
        assert event["payload"]["status"] == "live"


def test_ws_replay_respects_channel_filtering():
    """Verify replay filters events by the client's subscribed channels."""
    with client.websocket_connect("/api/ws?api_key=dev-operator-key") as ws:
        ws.receive_json()  # greeting

        # Subscribe specifically to 'actions'
        ws.send_json({
            "action": "subscribe",
            "channels": ["actions"],
        })
        ws.receive_json()  # confirmation

        # Request replay
        ws.send_json({
            "action": "replay",
            "limit": 20,
        })

        start = ws.receive_json()
        assert start["event_type"] == "REPLAY_STARTED"

        replayed = []
        msg = ws.receive_json()
        while msg.get("event_type") != "REPLAY_COMPLETE":
            replayed.append(msg)
            msg = ws.receive_json()

        assert msg["event_type"] == "REPLAY_COMPLETE"
        # If any events were replayed, all must match channel 'actions'
        for evt in replayed:
            assert evt["channel"] == "actions"


def test_ws_replay_viewer_role_masking():
    """Verify that during database replay, unprivileged VIEWER role receives redacted sensitive fields."""
    with client.websocket_connect("/api/ws?api_key=dev-viewer-key") as ws:
        ws.receive_json()  # greeting

        ws.send_json({
            "action": "replay",
            "limit": 10,
        })

        start = ws.receive_json()
        assert start["event_type"] == "REPLAY_STARTED"

        replayed = []
        msg = ws.receive_json()
        while msg.get("event_type") != "REPLAY_COMPLETE":
            replayed.append(msg)
            msg = ws.receive_json()

        assert msg["event_type"] == "REPLAY_COMPLETE"
        # Any replayed events should have sensitive keys masked if present
        sensitive_keys = {"token", "secret", "password", "api_key", "connection_string", "private_key"}
        for evt in replayed:
            payload = evt.get("payload", {})
            for k in payload:
                if k.lower() in sensitive_keys:
                    assert payload[k] == "[REDACTED]"


def test_ws_publish_async_coroutine():
    """Verify asynchronous publish_async broadcasts cleanly without deadlock."""
    import asyncio

    async def _runner():
        await default_event_manager.publish_async(
            event_type="ASYNC_EVENT",
            channel="orchestration",
            payload={"async_status": "ok"},
        )

    asyncio.run(_runner())
