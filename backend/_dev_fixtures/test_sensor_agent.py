"""Standalone test runner for Sensor/Event Intelligence Agent.

Run with: python backend/_dev_fixtures/test_sensor_agent.py

NOTE: This is the backward-compatible test runner. The canonical tests live
in backend/agents/sensor_event_intelligence/test_agent.py.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to sys.path if not present
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.agents.sensor_event_intelligence import SensorEventIntelligence
from backend.bus.event_bus import EventBus

FIXTURE_PATH = Path(__file__).parent / "raw_events.json"


async def main() -> int:
    print("==================================================")
    print("NOVA — Sensor/Event Intelligence Test Suite")
    print("==================================================")

    # 1. Setup fresh bus and agent
    bus = EventBus()
    agent = SensorEventIntelligence(bus_instance=bus)

    received_events: list[dict[str, Any]] = []

    async def _on_normalized(evt_dict: dict[str, Any]) -> None:
        received_events.append(evt_dict)

    await bus.subscribe("normalized.events", _on_normalized)
    await bus.start()
    await agent.start()

    # 2. Load fixture data
    if not FIXTURE_PATH.exists():
        print(f"[FAIL] Fixture file not found at {FIXTURE_PATH}")
        return 1

    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        raw_events = json.load(f)

    # 3. Publish events one by one with 0.1s delay
    for raw_evt in raw_events:
        await bus.publish("raw.telemetry", raw_evt)
        await asyncio.sleep(0.1)

    # Also publish a duplicate event_id to test deduplication
    duplicate_evt = raw_events[0]  # evt_001
    await bus.publish("raw.telemetry", duplicate_evt)
    await asyncio.sleep(0.1)

    # Give dispatch loop time to complete
    await asyncio.sleep(0.3)

    await agent.stop()
    await bus.shutdown()

    # 4. Assertions
    # NOTE: The refactored agent generates uuid4 event_ids, so we match by
    # value/zone/source instead of the original fixture event_id strings.
    failures: list[str] = []
    passed_count = 0

    def check(condition: bool, label: str, detail: str = "") -> None:
        nonlocal passed_count
        if condition:
            print(f"  [OK] PASSED: {label}")
            passed_count += 1
        else:
            msg = f"  [FAIL] FAILED: {label}"
            if detail:
                msg += f" — {detail}"
            print(msg)
            failures.append(label)

    # Helper: find events by value + zone
    def find_events(
        zone: str | None = None,
        source: str | None = None,
        value: float | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for e in received_events:
            if zone and e.get("zone_id") != zone:
                continue
            if source and e.get("source") != source:
                continue
            if value is not None and e.get("value") != value:
                continue
            results.append(e)
        return results

    # Assertion 1: evt_001 (200ppm, BAY-3, gas_sensor) -> severity_hint="normal"
    evt1_matches = find_events(zone="BAY-3", source="gas_sensor", value=200.0)
    check(
        len(evt1_matches) >= 1 and evt1_matches[0].get("severity_hint") == "normal",
        "evt_001 (200ppm) -> severity_hint='normal'",
        f"Got: {evt1_matches}",
    )

    # Assertion 2: evt_002 (216ppm) -> severity_hint="elevated"
    evt2_matches = find_events(zone="BAY-3", source="gas_sensor", value=216.0)
    check(
        len(evt2_matches) == 1 and evt2_matches[0].get("severity_hint") == "elevated",
        "evt_002 (216ppm) -> severity_hint='elevated'",
        f"Got: {evt2_matches}",
    )

    # Assertion 3: evt_007 (cctv confidence 0.91) -> received
    cctv_high = find_events(source="cctv")
    check(
        len(cctv_high) == 1,
        "evt_007 (cctv confidence 0.91) -> received",
        f"Got {len(cctv_high)} CCTV events",
    )

    # Assertion 4: evt_008 (Bay5, no permit/maintenance) -> compound_flag=False
    bay5_events = find_events(zone="BAY-5", source="gas_sensor")
    check(
        len(bay5_events) >= 1 and bay5_events[0].get("compound_flag") is False,
        "evt_008 (Bay5, no permit/maintenance) -> compound_flag=False",
        f"Got: {bay5_events}",
    )

    # Assertion 5: Bay3 window after permit+maintenance -> compound_flag=True on gas event
    bay3_compound = [
        e for e in received_events
        if e.get("zone_id") == "BAY-3"
        and e.get("source") == "gas_sensor"
        and e.get("compound_flag") is True
    ]
    check(
        len(bay3_compound) >= 1,
        "Bay3 window after permit+maintenance -> compound_flag=True on gas event",
        f"Got: {bay3_compound}",
    )

    # Assertion 6: Duplicate event_id -> only processed once
    evt1_count = len(find_events(zone="BAY-3", source="gas_sensor", value=200.0))
    check(
        evt1_count == 1,
        "Duplicate event_id -> only processed once",
        f"evt_001 appeared {evt1_count} times in normalized.events",
    )

    # Assertion 7: CCTV event with confidence 0.5 -> dropped
    low_conf = [
        e for e in received_events
        if e.get("source") == "cctv"
        and e.get("metadata", {}).get("confidence") == 0.5
    ]
    check(
        len(low_conf) == 0,
        "CCTV event with confidence 0.5 -> dropped",
        f"Found unexpectedly: {low_conf}",
    )

    print("==================================================")
    print(f"RESULTS: {passed_count} passed, {len(failures)} failed")
    print("==================================================")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
