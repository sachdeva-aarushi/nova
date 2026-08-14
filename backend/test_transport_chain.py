#!/usr/bin/env python
"""
backend/test_transport_chain.py — End-to-end transport chain test.

Tests two chains:
1. SIMULATOR → EVENT BUS → FACTORY STATE → WEBSOCKET → FRONTEND
2. FRONTEND → WEBSOCKET → BACKEND ROUTE → AGENTS → RESPONSE

Usage:
    python -m backend.test_transport_chain

Requirements:
    - Backend running on localhost:8000
    - Frontend can connect via WebSocket
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import aiohttp
    import websockets
except ImportError:
    print("❌ Missing dependencies. Install with: pip install aiohttp websockets")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────── #
# Configuration                                                                #
# ─────────────────────────────────────────────────────────────────────────── #

BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
SESSION_ID = f"test-{datetime.now(tz=timezone.utc).isoformat()}"

# Test timing
CONNECT_TIMEOUT = 5.0
EVENT_WAIT_TIME = 1.0
CHAIN_TEST_TIMEOUT = 10.0

# ─────────────────────────────────────────────────────────────────────────── #
# Chain 1: Simulator → Frontend                                                #
# ─────────────────────────────────────────────────────────────────────────── #


class Chain1Tester:
    """Test the data flow: simulator → event bus → WS → frontend."""

    def __init__(self):
        self.received_messages: list[dict[str, Any]] = []
        self.ws_status = "disconnected"
        self.event_counts: dict[str, int] = {}

    async def connect_websocket(self) -> bool:
        """Establish WebSocket connection to the backend."""
        try:
            logger.info("🔌 Connecting WebSocket to %s/ws/session/%s", WS_URL, SESSION_ID)
            self.ws = await asyncio.wait_for(
                websockets.connect(f"{WS_URL}/ws/session/{SESSION_ID}"),
                timeout=CONNECT_TIMEOUT,
            )
            self.ws_status = "connected"
            logger.info("✅ WebSocket connected")

            # Start receive loop
            asyncio.create_task(self._receive_loop())
            return True

        except asyncio.TimeoutError:
            logger.error("❌ WebSocket connection timed out")
            return False
        except Exception as exc:
            logger.error("❌ WebSocket connection failed: %s", exc)
            return False

    async def _receive_loop(self) -> None:
        """Listen for messages from the WebSocket."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    self.received_messages.append(data)
                    self.event_counts[msg_type] = self.event_counts.get(msg_type, 0) + 1
                    logger.info("📨 Received WS message: type=%s", msg_type)
                except json.JSONDecodeError:
                    logger.warning("⚠️  Received non-JSON message: %s", message[:100])
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("❌ WebSocket receive error: %s", exc)
            self.ws_status = "error"

    async def test_chain_1(self) -> dict[str, Any]:
        """Run Chain 1 test: publish a test event and verify it reaches frontend."""
        logger.info("\n" + "=" * 80)
        logger.info("CHAIN 1 TEST: Simulator → EventBus → WebSocket → Frontend")
        logger.info("=" * 80)

        # Clear previous messages
        self.received_messages.clear()
        self.event_counts.clear()

        # 1. Publish test event via API
        test_event = {
            "event_id": f"test-chain1-{datetime.now(tz=timezone.utc).isoformat()}",
            "source": "gas_sensor",
            "zone_id": "Test-Bay-1",
            "value": 150.5,
            "severity_hint": "elevated",
            "metadata": {"test": True, "chain": 1},
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        }

        logger.info("📤 Publishing test event: %s", json.dumps(test_event)[:150])

        async with aiohttp.ClientSession() as session:
            # Use the debug endpoint
            url = f"{BACKEND_URL}/api/debug/transport/test"
            params = {"topic": "raw.telemetry"}
            
            try:
                async with session.post(url, params=params) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info("✅ Test event published via API")
                        logger.info("   Events published: %d", result.get("events_published", 0))
                        logger.info("   Broadcasts sent: %d", result.get("broadcasts_sent", 0))
                        logger.info("   By topic: %s", result.get("by_topic"))
                    else:
                        logger.error("❌ API request failed: %d", resp.status)
                        logger.error("   Response: %s", await resp.text())
                        return {"success": False, "error": "API request failed"}

            except Exception as exc:
                logger.error("❌ Failed to publish test event: %s", exc)
                return {"success": False, "error": str(exc)}

        # 2. Wait for messages
        logger.info("⏳ Waiting %s seconds for WebSocket messages...", EVENT_WAIT_TIME)
        await asyncio.sleep(EVENT_WAIT_TIME)

        # 3. Check results
        success = len(self.received_messages) > 0
        raw_telemetry_msgs = self.event_counts.get("raw.telemetry", 0)

        logger.info("\n📊 Chain 1 Results:")
        logger.info("   Total messages received: %d", len(self.received_messages))
        logger.info("   By type: %s", self.event_counts)
        logger.info("   Connection status: %s", self.ws_status)

        if raw_telemetry_msgs > 0:
            logger.info("✅ Chain 1 SUCCESS: raw.telemetry event reached frontend")
        else:
            logger.error("❌ Chain 1 FAILED: No raw.telemetry messages received")

        return {
            "success": success,
            "total_messages": len(self.received_messages),
            "event_counts": self.event_counts,
            "ws_status": self.ws_status,
            "messages": self.received_messages[-5:] if self.received_messages else [],
        }

    async def close(self) -> None:
        """Close WebSocket connection."""
        if hasattr(self, "ws") and self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────── #
# Chain 2: Frontend → Backend (Voice)                                          #
# ─────────────────────────────────────────────────────────────────────────── #


class Chain2Tester:
    """Test the data flow: frontend voice → backend → agents → response."""

    async def test_chain_2(self) -> dict[str, Any]:
        """Test voice input path: frontend → backend route → agent."""
        logger.info("\n" + "=" * 80)
        logger.info("CHAIN 2 TEST: Frontend Voice → Backend Routes → Agents")
        logger.info("=" * 80)

        # Test via the agent query endpoint (routes_voice_command.py)
        test_command = "check the gas levels in bay 1"
        logger.info("🎤 Test command: '%s'", test_command)

        async with aiohttp.ClientSession() as session:
            url = f"{BACKEND_URL}/api/voice/query"
            payload = {
                "text": test_command,
                "case_id": "test-chain2",
            }

            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status in (200, 202):
                        result = await resp.json()
                        logger.info("✅ Voice query sent successfully")
                        logger.info("   Response type: %s", result.get("response", "")[:100])
                        logger.info("   Tool calls: %d", len(result.get("tool_calls", [])))
                        return {
                            "success": True,
                            "status_code": resp.status,
                            "response": result,
                        }
                    else:
                        logger.error("❌ Voice query failed: %d", resp.status)
                        body = await resp.text()
                        logger.error("   Response: %s", body[:200])
                        return {
                            "success": False,
                            "status_code": resp.status,
                            "error": body,
                        }

            except Exception as exc:
                logger.error("❌ Voice query test failed: %s", exc)
                return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────── #
# Diagnostics                                                                  #
# ─────────────────────────────────────────────────────────────────────────── #


async def run_diagnostics() -> dict[str, Any]:
    """Check system health and connectivity."""
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTICS: System Health Check")
    logger.info("=" * 80)

    diagnostics = {}

    # 1. Backend health
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info("✅ Backend health: OK")
                    diagnostics["backend"] = {"healthy": True, "data": data}
                else:
                    logger.error("❌ Backend health: FAILED (%d)", resp.status)
                    diagnostics["backend"] = {"healthy": False, "status": resp.status}
    except Exception as exc:
        logger.error("❌ Backend unreachable: %s", exc)
        diagnostics["backend"] = {"healthy": False, "error": str(exc)}
        return diagnostics

    # 2. Debug transport state
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/debug/transport/state") as resp:
                if resp.status == 200:
                    state = await resp.json()
                    logger.info("✅ Debug transport active")
                    logger.info("   Event bus subscriptions: %d", state.get("event_bus", {}).get("subscriptions", 0))
                    logger.info("   WebSocket connections: %d", state.get("websocket_connections", {}).get("total_clients", 0))
                    diagnostics["debug_transport"] = state
                else:
                    logger.warning("⚠️  Debug transport not available")
    except Exception as exc:
        logger.warning("⚠️  Debug transport unavailable: %s", exc)

    # 3. Subscriptions
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/debug/subscriptions") as resp:
                if resp.status == 200:
                    subs = await resp.json()
                    logger.info("✅ Event bus subscriptions:")
                    for topic, handlers in subs.get("by_topic", {}).items():
                        logger.info("   %s: %d handlers", topic, len(handlers))
                    diagnostics["subscriptions"] = subs
    except Exception:
        pass

    return diagnostics


# ─────────────────────────────────────────────────────────────────────────── #
# Main                                                                         #
# ─────────────────────────────────────────────────────────────────────────── #


async def main() -> int:
    """Run all tests."""
    logger.info("🚀 NOVA Transport Chain Test Suite")
    logger.info("Session ID: %s", SESSION_ID)

    # 1. Diagnostics
    diagnostics = await run_diagnostics()

    # 2. Chain 1 Test
    chain1 = Chain1Tester()
    connected = await chain1.connect_websocket()

    if not connected:
        logger.error("❌ Cannot proceed without WebSocket connection")
        return 1

    try:
        chain1_result = await chain1.test_chain_1()
    except Exception as exc:
        logger.error("❌ Chain 1 test crashed: %s", exc)
        chain1_result = {"success": False, "error": str(exc)}
    finally:
        await chain1.close()

    # 3. Chain 2 Test
    chain2 = Chain2Tester()
    try:
        chain2_result = await chain2.test_chain_2()
    except Exception as exc:
        logger.error("❌ Chain 2 test crashed: %s", exc)
        chain2_result = {"success": False, "error": str(exc)}

    # 4. Summary
    logger.info("\n" + "=" * 80)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 80)

    chain1_status = "✅ PASS" if chain1_result.get("success") else "❌ FAIL"
    chain2_status = "✅ PASS" if chain2_result.get("success") else "❌ FAIL"

    logger.info("Chain 1 (Simulator → Frontend): %s", chain1_status)
    if not chain1_result.get("success"):
        logger.info("  Error: %s", chain1_result.get("error"))
        logger.info("  Details: messages=%d, status=%s", 
                   chain1_result.get("total_messages", 0),
                   chain1_result.get("ws_status"))

    logger.info("Chain 2 (Frontend Voice → Backend): %s", chain2_status)
    if not chain2_result.get("success"):
        logger.info("  Error: %s", chain2_result.get("error"))

    logger.info("\n🔗 Debug Output:")
    logger.info("  Backend: %s", diagnostics.get("backend", {}).get("healthy"))
    
    if "subscriptions" in diagnostics:
        sub_count = diagnostics["subscriptions"].get("total_subscriptions", 0)
        logger.info("  Event Bus Subscriptions: %d", sub_count)

    # Exit code: 0 if all pass, 1 if any fail
    all_pass = chain1_result.get("success") and chain2_result.get("success")
    
    if all_pass:
        logger.info("\n✅ ALL TESTS PASSED")
    else:
        logger.info("\n❌ SOME TESTS FAILED")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
