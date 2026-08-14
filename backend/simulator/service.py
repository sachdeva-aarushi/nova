"""
backend/simulator/service.py — Internal background data simulator service.

Runs inside FastAPI's lifespan when SIMULATOR_ENABLED is active (default: true).
Directly publishes scenario events onto the backend EventBus (raw.telemetry topic),
triggering the multi-agent pipeline and WebSocket bridge without external HTTP calls or separate processes.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.bus.event_bus import EventBus

logger = logging.getLogger("vigil.simulator")

_SCENARIOS_DIR = Path(__file__).parent.parent.parent / "data_simulator" / "scenarios"


class BackgroundSimulatorService:
    """
    Internal background data simulator service.
    Directly feeds events into the EventBus during application lifespan.
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        enabled = os.environ.get("SIMULATOR_ENABLED", "true").lower() in ("true", "1")
        if not enabled:
            logger.info("Internal Simulator Service is disabled (SIMULATOR_ENABLED=false)")
            return

        scenario_id = os.environ.get("SIMULATOR_SCENARIO", "hero_scenario")
        speed = float(os.environ.get("SIMULATOR_SPEED", "2.0"))

        if self._running:
            logger.warning("Internal Simulator Service already running")
            return

        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(scenario_id, speed),
            name="background_simulator_service",
        )
        logger.info("Internal Simulator Service started: scenario=%s speed=%.1fx", scenario_id, speed)

    async def _run_loop(self, scenario_id: str, speed: float) -> None:
        from data_simulator.event_generator import ScenarioRunner

        runner = ScenarioRunner(self.bus)
        scenario_path = str(_SCENARIOS_DIR / f"{scenario_id}.json")

        while self._running:
            try:
                logger.info("Internal Simulator loading scenario '%s' (speed %.1fx)...", scenario_id, speed)
                await runner.load(scenario_path)
                await runner.play(speed_multiplier=speed)
                if not self._running:
                    break
                logger.info("Internal Simulator completed scenario '%s'. Replaying in 2s...", scenario_id)
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                logger.info("Internal Simulator task cancelled")
                break
            except Exception as exc:
                logger.error("Internal Simulator encountered error: %s", exc)
                await asyncio.sleep(5.0)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Internal Simulator Service stopped cleanly")
