"""
backend/debug_transport.py — Trace data flow through the entire stack.

Usage (in FastAPI lifespan or routes):
    from backend.debug_transport import DebugTransport
    
    debug = DebugTransport()
    await debug.enable()  # Patches bus, ws_bridge, socket handlers
    
    # Now all events are logged with detailed tracing:
    # - bus.publish() → logs topic, event, subscribers matched
    # - ws_bridge handlers → logs broadcast calls
    # - ws_session messages → logs send_json calls
    # - WebSocket broadcasts → logs to all clients
    
    # Query state:
    state = debug.get_state()
    print(f"Events in flight: {len(state['events_published'])}")
    print(f"WebSocket broadcasts: {len(state['broadcasts'])}")
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DebugTransport:
    """Instrument the entire transport chain for debugging."""

    def __init__(self) -> None:
        self.enabled = False
        self.max_events = 200
        self.max_broadcasts = 200
        self.max_ws_messages = 200
        self._events_published: deque[dict[str, Any]] = deque(maxlen=self.max_events)
        self._broadcasts: deque[dict[str, Any]] = deque(maxlen=self.max_broadcasts)
        self._ws_messages: deque[dict[str, Any]] = deque(maxlen=self.max_ws_messages)
        self._original_bus_publish: Callable | None = None
        self._original_bus_subscribe: Callable | None = None
        self._original_manager_broadcast: Callable | None = None
        self._original_ws_send_json: Callable | None = None

    def record_event(self, entry: dict[str, Any]) -> None:
        """Store only the most recent activity for diagnostics."""
        if len(self._events_published) >= self.max_events:
            self._events_published.popleft()
        self._events_published.append(entry)

    def record_broadcast(self, entry: dict[str, Any]) -> None:
        """Store only the most recent broadcast activity."""
        if len(self._broadcasts) >= self.max_broadcasts:
            self._broadcasts.popleft()
        self._broadcasts.append(entry)

    def record_ws_message(self, entry: dict[str, Any]) -> None:
        """Store only the most recent websocket activity."""
        if len(self._ws_messages) >= self.max_ws_messages:
            self._ws_messages.popleft()
        self._ws_messages.append(entry)

    async def enable(self) -> None:
        """Patch the event bus, WebSocket manager, and connection manager."""
        if self.enabled:
            logger.warning("DebugTransport already enabled")
            return

        from backend.bus.event_bus import bus
        from backend.api.ws_session import manager

        # 1. Patch bus.publish() to log all events
        self._original_bus_publish = bus.publish

        async def logged_publish(topic: str, event: dict[str, Any]) -> None:
            entry = {
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "topic": topic,
                "event": event,
                "subscribers_count": len(bus._subscribers.get(topic, [])),
                "matched_subscriptions": self._count_matches(topic),
            }
            self.record_event(entry)
            logger.info(
                "🔵 EventBus.publish(%s) — %d/%d subscribers | event=%s",
                topic,
                entry["matched_subscriptions"],
                len(bus._subscribers),
                json.dumps(event, default=str)[:100],
            )
            await self._original_bus_publish(topic, event)

        bus.publish = logged_publish

        # 2. Patch manager.broadcast() to log WS pushes
        self._original_manager_broadcast = manager.broadcast

        async def logged_broadcast(session_id: str, message: dict[str, Any]) -> None:
            msg_type = message.get("type", "unknown")
            entry = {
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "session_id": session_id,
                "message_type": msg_type,
                "payload": message.get("payload"),
                "connection_count": len(manager._connections.get(session_id, set())),
            }
            self.record_broadcast(entry)
            logger.info(
                "📤 WS broadcast(%s) type=%s → %d connections",
                session_id,
                msg_type,
                entry["connection_count"],
            )
            await self._original_manager_broadcast(session_id, message)

        manager.broadcast = logged_broadcast

        # 3. Patch manager.broadcast_all() similarly
        original_broadcast_all = manager.broadcast_all

        async def logged_broadcast_all(message: dict[str, Any]) -> None:
            msg_type = message.get("type", "unknown")
            total_conns = sum(len(conns) for conns in manager._connections.values())
            entry = {
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "message_type": msg_type,
                "payload": message.get("payload"),
                "total_connections": total_conns,
                "sessions": len(manager._connections),
            }
            self.record_broadcast(entry)
            logger.info(
                "📤 WS broadcast_all(%s) → %d total connections across %d sessions",
                msg_type,
                total_conns,
                len(manager._connections),
            )
            await original_broadcast_all(message)

        manager.broadcast_all = logged_broadcast_all

        # 4. Patch bus.subscribe() to track subscriptions
        self._original_bus_subscribe = bus.subscribe

        async def logged_subscribe(topic: str, handler: Callable) -> None:
            logger.info("🔗 EventBus.subscribe(%s) ← %s", topic, handler.__name__)
            await self._original_bus_subscribe(topic, handler)

        bus.subscribe = logged_subscribe

        self.enabled = True
        logger.info("✅ DebugTransport enabled — all events will be logged")

    def _count_matches(self, event_topic: str) -> int:
        """Count how many subscriptions match the given event topic."""
        from backend.bus.event_bus import _matches, bus

        count = 0
        for sub_topic in bus._subscribers.keys():
            if _matches(sub_topic, event_topic):
                count += len(bus._subscribers[sub_topic])
        return count

    def get_state(self) -> dict[str, Any]:
        """Return current state of all observed events."""
        return {
            "enabled": self.enabled,
            "events_published_count": len(self._events_published),
            "broadcasts_count": len(self._broadcasts),
            "ws_messages_count": len(self._ws_messages),
            "recent_events": list(self._events_published)[-10:] if self._events_published else [],
            "recent_broadcasts": list(self._broadcasts)[-10:] if self._broadcasts else [],
            "by_topic": self._group_by_topic(),
            "by_broadcast_type": self._group_broadcasts_by_type(),
        }

    def _group_by_topic(self) -> dict[str, int]:
        """Count events by topic."""
        by_topic: dict[str, int] = {}
        for entry in self._events_published:
            topic = entry["topic"]
            by_topic[topic] = by_topic.get(topic, 0) + 1
        return by_topic

    def _group_broadcasts_by_type(self) -> dict[str, int]:
        """Count broadcasts by message type."""
        by_type: dict[str, int] = {}
        for entry in self._broadcasts:
            msg_type = entry["message_type"]
            by_type[msg_type] = by_type.get(msg_type, 0) + 1
        return by_type

    def dump_json(self) -> str:
        """Return full state as JSON for inspection."""
        return json.dumps(self.get_state(), default=str, indent=2)

    def clear(self) -> None:
        """Clear all logged events."""
        self._events_published.clear()
        self._broadcasts.clear()
        self._ws_messages.clear()
        logger.info("DebugTransport cleared")


# Module-level singleton
debug_transport = DebugTransport()
