"""
backend/api/routes_debug.py — Debug endpoints for transport chain inspection.

Endpoints:
  GET  /api/debug/transport/state      — Current event bus & WS state
  POST /api/debug/transport/test       — Run a test event through the chain
  POST /api/debug/transport/clear      — Clear logged events
  GET  /api/debug/subscriptions        — List all event bus subscriptions
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(tags=["debug"], prefix="/api/debug")


# ─── Transport State ───────────────────────────────────────────────────── #


@router.get("/transport/state")
async def get_transport_state() -> dict[str, Any]:
    """Get current event bus and WebSocket state."""
    try:
        from backend.debug_transport import debug_transport
        from backend.bus.event_bus import bus
        from backend.api.ws_session import manager

        state = debug_transport.get_state()

        # Add live bus info
        state["event_bus"] = {
            "running": bus._running,
            "subscriptions": len(bus._subscribers),
            "queue_size": bus._queue.qsize(),
            "topics": {
                topic: len(handlers) for topic, handlers in bus._subscribers.items()
            },
        }

        # Add live WebSocket info
        state["websocket_connections"] = {
            "sessions": len(manager._connections),
            "total_clients": sum(len(conns) for conns in manager._connections.values()),
            "by_session": {
                sid: len(conns) for sid, conns in manager._connections.items()
            },
        }

        return state

    except Exception as exc:
        logger.error("Failed to get transport state: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transport/test")
async def test_transport_chain(topic: str = "raw.telemetry") -> dict[str, Any]:
    """
    Publish a test event and trace its journey through the system.

    Query params:
      topic: Event topic to publish to (default: raw.telemetry)

    Returns the test event details and a summary of broadcasts it triggered.
    """
    try:
        from backend.debug_transport import debug_transport
        from backend.bus.event_bus import bus

        if not debug_transport.enabled:
            raise HTTPException(
                status_code=400,
                detail="DebugTransport not enabled. Start the app in debug mode.",
            )

        # Clear previous state
        debug_transport.clear()

        # Create a test event
        test_event = {
            "event_id": "test-" + datetime.now(tz=timezone.utc).isoformat(),
            "source": "test",
            "zone_id": "Test-Zone",
            "value": 123.45,
            "severity_hint": "elevated",
            "metadata": {"test": True},
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        }

        # Publish and wait for dispatch
        await bus.publish(topic, test_event)
        await asyncio.sleep(0.5)  # Let dispatch loop process

        # Get the resulting state
        state = debug_transport.get_state()

        return {
            "test_event": test_event,
            "topic": topic,
            "events_published": state["events_published_count"],
            "broadcasts_sent": state["broadcasts_count"],
            "by_topic": state["by_topic"],
            "by_broadcast_type": state["by_broadcast_type"],
            "recent_events": state["recent_events"],
            "recent_broadcasts": state["recent_broadcasts"],
        }

    except Exception as exc:
        logger.error("Transport test failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transport/clear")
async def clear_transport_logs() -> dict[str, str]:
    """Clear all logged transport events."""
    try:
        from backend.debug_transport import debug_transport

        debug_transport.clear()
        return {"status": "cleared"}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Subscriptions ───────────────────────────────────────────────────── #


@router.get("/subscriptions")
async def list_subscriptions() -> dict[str, Any]:
    """List all event bus subscriptions."""
    try:
        from backend.bus.event_bus import bus

        subscriptions = {}
        for topic, handlers in bus._subscribers.items():
            subscriptions[topic] = [h.__name__ for h in handlers]

        return {
            "total_subscriptions": len(bus._subscribers),
            "by_topic": subscriptions,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── WebSocket Connections ──────────────────────────────────────────────── #


@router.get("/ws/connections")
async def list_ws_connections() -> dict[str, Any]:
    """List all active WebSocket connections."""
    try:
        from backend.api.ws_session import manager

        return {
            "total_sessions": len(manager._connections),
            "total_connections": sum(
                len(conns) for conns in manager._connections.values()
            ),
            "sessions": {
                sid: {"client_count": len(conns)} for sid, conns in manager._connections.items()
            },
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
