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
