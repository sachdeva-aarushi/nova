#!/usr/bin/env python
"""
backend/analyze_transport.py — Static analysis of transport chain code.

Identifies common breakage patterns in the event bus, WebSocket bridge, 
and frontend socket handler code.

Usage:
    python -m backend.analyze_transport
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────── #
# Analysis Checks                                                              #
# ─────────────────────────────────────────────────────────────────────────── #


class TransportAnalyzer:
    """Analyze transport chain code for common issues."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.issues: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.info: list[dict[str, Any]] = []

    def add_issue(self, severity: str, file: str, line: int | None, message: str) -> None:
        """Log an issue found during analysis."""
        entry = {
            "severity": severity,
            "file": str(file),
            "line": line,
            "message": message,
        }
        if severity == "ERROR":
            self.issues.append(entry)
        elif severity == "WARNING":
            self.warnings.append(entry)
        else:
            self.info.append(entry)

    # ── Chain 1: Event Bus → WebSocket ──────────────────────────────────── #

    def check_ws_bridge_subscribed(self) -> None:
        """Verify ws_bridge is subscribed to raw.telemetry."""
        ws_session_path = self.repo_root / "backend/api/ws_session.py"
        
        if not ws_session_path.exists():
            self.add_issue("ERROR", ws_session_path, None, "File not found")
            return

        with open(ws_session_path) as f:
            content = f.read()

        # Check for subscription to raw.telemetry
        if 'subscribe("raw.telemetry"' in content or "subscribe('raw.telemetry'" in content:
            self.add_issue("INFO", ws_session_path, None, 
                          "✅ raw.telemetry subscription found")
        else:
            self.add_issue("ERROR", ws_session_path, None,
                          "❌ CRITICAL: No subscription to raw.telemetry found in ws_bridge")

    def check_manager_broadcast_exists(self) -> None:
        """Verify ConnectionManager.broadcast_all() method exists."""
        ws_session_path = self.repo_root / "backend/api/ws_session.py"

        if not ws_session_path.exists():
            return

        with open(ws_session_path) as f:
            content = f.read()

        if "async def broadcast_all" in content:
            self.add_issue("INFO", ws_session_path, None,
                          "✅ broadcast_all() method found in ConnectionManager")
        else:
            self.add_issue("WARNING", ws_session_path, None,
                          "⚠️ No broadcast_all() method in ConnectionManager")

    def check_event_bus_dispatch_loop(self) -> None:
        """Check event bus dispatch loop is implemented."""
        bus_path = self.repo_root / "backend/bus/event_bus.py"

        if not bus_path.exists():
            self.add_issue("ERROR", bus_path, None, "File not found")
            return

        with open(bus_path) as f:
            content = f.read()

        if "async def _dispatch_loop" in content:
            self.add_issue("INFO", bus_path, None,
                          "✅ _dispatch_loop() method found in EventBus")

            # Check for fire-and-forget with asyncio.create_task
            if "asyncio.create_task" in content:
                self.add_issue("INFO", bus_path, None,
                              "✅ Using asyncio.create_task for fire-and-forget")
            else:
                self.add_issue("WARNING", bus_path, None,
                              "⚠️ Possible blocking in dispatch loop - check for awaits")
        else:
            self.add_issue("ERROR", bus_path, None,
                          "❌ CRITICAL: _dispatch_loop() not found")

    def check_bus_start_called(self) -> None:
        """Verify bus.start() is called in FastAPI lifespan."""
        main_path = self.repo_root / "backend/main.py"

        if not main_path.exists():
            self.add_issue("ERROR", main_path, None, "File not found")
            return

        with open(main_path) as f:
            content = f.read()

        if "await bus.start()" in content:
            self.add_issue("INFO", main_path, None,
                          "✅ bus.start() called in lifespan")
        else:
            self.add_issue("ERROR", main_path, None,
                          "❌ CRITICAL: bus.start() not called in lifespan")

        if "await start_ws_bridge(bus)" in content:
            self.add_issue("INFO", main_path, None,
                          "✅ start_ws_bridge(bus) called in lifespan")
        else:
            self.add_issue("ERROR", main_path, None,
                          "❌ CRITICAL: start_ws_bridge(bus) not called")

    # ── Chain 2: Frontend Socket Handler ────────────────────────────────── #

    def check_frontend_socket_handler(self) -> None:
        """Check frontend socket handler has all necessary message types."""
        socket_path = self.repo_root / "frontend/src/ws/useSessionSocket.ts"

        if not socket_path.exists():
            self.add_issue("WARNING", socket_path, None, "Socket handler not found")
            return

        with open(socket_path) as f:
            content = f.read()

        required_cases = [
            ("connection.status", "WebSocket connection status"),
            ("raw.telemetry", "Raw sensor telemetry from simulator"),
            ("risk.updated", "Risk assessment updates"),
            ("case.state_changed", "Case state transitions"),
        ]

        for case_type, description in required_cases:
            if f"case '{case_type}'" in content:
                self.add_issue("INFO", socket_path, None,
                              f"✅ Handler for '{case_type}' found")
            else:
                self.add_issue("WARNING", socket_path, None,
                              f"⚠️ No handler for '{case_type}' ({description})")

    def check_zustand_store_update_methods(self) -> None:
        """Check Zustand stores have update methods for sensor data."""
        demo_store = self.repo_root / "frontend/src/store/useDemoStore.ts"
        case_store = self.repo_root / "frontend/src/store/useCaseStore.ts"

        for store_path, store_name in [(demo_store, "useDemoStore"), (case_store, "useCaseStore")]:
            if not store_path.exists():
                self.add_issue("WARNING", store_path, None, f"{store_name} not found")
                continue

            with open(store_path) as f:
                content = f.read()

            if "updateSensor" in content or "addTickerItem" in content or "appendEvidence" in content:
                self.add_issue("INFO", store_path, None,
                              f"✅ Update methods found in {store_name}")
            else:
                self.add_issue("WARNING", store_path, None,
                              f"⚠️ No update methods found in {store_name}")

    # ── Voice Agent Chain ──────────────────────────────────────────────── #

    def check_voice_routes_exist(self) -> None:
        """Check voice command routes are registered."""
        voice_routes = self.repo_root / "backend/api/routes_voice_command.py"

        if voice_routes.exists():
            self.add_issue("INFO", voice_routes, None,
                          "✅ Voice command routes file found")
        else:
            self.add_issue("WARNING", voice_routes, None,
                          "⚠️ Voice command routes not found")

    def check_voice_agent_exists(self) -> None:
        """Check voice agent is implemented."""
        voice_agent = self.repo_root / "backend/agents/voice_agent.py"

        if voice_agent.exists():
            self.add_issue("INFO", voice_agent, None,
                          "✅ Voice agent found")
        else:
            self.add_issue("WARNING", voice_agent, None,
                          "⚠️ Voice agent not found")

    # ── Sensor Event Intelligence ──────────────────────────────────────── #

    def check_sensor_intelligence_subscribed(self) -> None:
        """Check sensor intelligence is subscribed to raw.telemetry."""
        agent_path = self.repo_root / "backend/agents/sensor_event_intelligence.py"
        agent_dir = self.repo_root / "backend/agents/sensor_event_intelligence"

        # Check which one exists
        if agent_path.exists():
            path = agent_path
        elif agent_dir.exists():
            agent_file = agent_dir / "agent.py"
            if agent_file.exists():
                path = agent_file
            else:
                path = agent_dir
        else:
            self.add_issue("WARNING", agent_path, None,
                          "⚠️ Sensor intelligence agent not found")
            return

        with open(path) as f:
            content = f.read()

        if "raw.telemetry" in content:
            self.add_issue("INFO", path, None,
                          "✅ raw.telemetry mentioned in sensor intelligence")
        else:
            self.add_issue("WARNING", path, None,
                          "⚠️ raw.telemetry not found in sensor intelligence")

    # ── Simulator Publishing ────────────────────────────────────────────── #

    def check_simulator_publishes_to_bus(self) -> None:
        """Check simulator publishes to event bus."""
        sim_path = self.repo_root / "data_simulator/event_generator.py"

        if not sim_path.exists():
            self.add_issue("WARNING", sim_path, None, "Simulator not found")
            return

        with open(sim_path) as f:
            content = f.read()

        if 'await self._bus.publish("raw.telemetry"' in content:
            self.add_issue("INFO", sim_path, None,
                          "✅ Simulator publishes to raw.telemetry")
        else:
            self.add_issue("ERROR", sim_path, None,
                          "❌ Simulator not publishing to raw.telemetry")

    # ── Run all checks ──────────────────────────────────────────────────── #

    def run_all_checks(self) -> int:
        """Run all analysis checks."""
        print("\n" + "=" * 80)
        print("🔍 NOVA Transport Chain Static Analysis")
        print("=" * 80)

        # Chain 1: Simulator → Frontend
        print("\n📊 Chain 1: Simulator → EventBus → WebSocket → Frontend")
        self.check_simulator_publishes_to_bus()
        self.check_event_bus_dispatch_loop()
        self.check_bus_start_called()
        self.check_ws_bridge_subscribed()
        self.check_manager_broadcast_exists()

        # Chain 2: Frontend → Backend  
        print("\n📊 Chain 2: Frontend → Backend Agents")
        self.check_voice_routes_exist()
        self.check_voice_agent_exists()
        self.check_sensor_intelligence_subscribed()

        # Frontend State Management
        print("\n📊 Frontend State Management")
        self.check_frontend_socket_handler()
        self.check_zustand_store_update_methods()

        # Print results
        print("\n" + "=" * 80)
        print("📋 Results Summary")
        print("=" * 80)

        print(f"\n❌ ERRORS: {len(self.issues)}")
        for issue in self.issues:
            print(f"   {issue['file']}: {issue['message']}")

        print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
        for warning in self.warnings:
            print(f"   {warning['file']}: {warning['message']}")

        print(f"\n✅ INFO: {len(self.info)}")
        for info in self.info[:5]:  # Show first 5
            print(f"   {info['file']}: {info['message']}")

        # Exit code: 0 if no errors, 1 if errors found
        return 0 if len(self.issues) == 0 else 1


def main() -> int:
    """Main entry point."""
    repo_root = Path(__file__).resolve().parent.parent

    analyzer = TransportAnalyzer(repo_root)
    return analyzer.run_all_checks()


if __name__ == "__main__":
    sys.exit(main())
