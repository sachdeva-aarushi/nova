"""backend/api/routes_factory.py — Factory state API endpoints.

Provides real-time factory floor data: sensor readings, zone status,
equipment health, production KPIs, and personnel headcount.
"""

from __future__ import annotations

import math
import random
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/factory", tags=["factory"])

# ──────────────────────────────────────────────────────────────────────────────
# STATIC ZONE LAYOUT (SVG coordinates, for heatmap rendering)
# ──────────────────────────────────────────────────────────────────────────────

ZONE_LAYOUT = [
    {
        "zone_id": "Bay1",
        "label": "Bay 1 — Feedstock Storage",
        "x": 40, "y": 60, "width": 140, "height": 120,
        "equipment_ids": ["T-01", "T-02", "T-03", "T-07"],
    },
    {
        "zone_id": "Bay2",
        "label": "Bay 2 — Pre-Treatment",
        "x": 200, "y": 60, "width": 140, "height": 120,
        "equipment_ids": ["HX-01", "HX-02", "PLC-01", "TK-22"],
    },
    {
        "zone_id": "Bay3",
        "label": "Bay 3 — Refining Unit (ACTIVE ALERT)",
        "x": 360, "y": 60, "width": 140, "height": 120,
        "equipment_ids": ["C-14", "P-08", "GD-B3-01", "GD-B3-02"],
    },
    {
        "zone_id": "Bay4",
        "label": "Bay 4 — Reactor Block",
        "x": 520, "y": 60, "width": 140, "height": 120,
        "equipment_ids": ["R-22", "R-23", "PRV-22", "HX-04"],
    },
    {
        "zone_id": "Bay5",
        "label": "Bay 5 — Product Finishing",
        "x": 40, "y": 200, "width": 620, "height": 80,
        "equipment_ids": ["SEP-01", "SEP-02", "PKG-01", "PKG-02", "SCAFFOLD-B5"],
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# EQUIPMENT REGISTRY (static metadata)
# ──────────────────────────────────────────────────────────────────────────────

EQUIPMENT_REGISTRY = {
    "C-14": {
        "name": "Compressor C-14", "class": "compressor", "zone_id": "Bay3",
        "rated_pressure_bar": 8.5, "last_serviced_daysago": 0.08, "status_nominal": "operational",
        "criticality": "critical",
    },
    "P-08": {
        "name": "Cooling Water Pump P-08", "class": "pump", "zone_id": "Bay3",
        "rated_flow_m3hr": 800, "last_serviced_daysago": 21, "status_nominal": "operational",
        "criticality": "high",
    },
    "R-22": {
        "name": "Reactor R-22", "class": "reactor", "zone_id": "Bay4",
        "rated_pressure_bar": 14.5, "last_serviced_daysago": 47, "status_nominal": "overdue_maintenance",
        "criticality": "critical",
    },
    "R-23": {
        "name": "Reactor R-23", "class": "reactor", "zone_id": "Bay4",
        "rated_pressure_bar": 14.5, "last_serviced_daysago": 12, "status_nominal": "operational",
        "criticality": "critical",
    },
    "T-07": {
        "name": "Storage Tank T-07", "class": "storage_tank", "zone_id": "Bay1",
        "last_serviced_daysago": 35, "status_nominal": "operational",
        "criticality": "high",
    },
    "HX-01": {
        "name": "Heat Exchanger HX-01", "class": "heat_exchanger", "zone_id": "Bay2",
        "last_serviced_daysago": 8, "status_nominal": "operational",
        "criticality": "medium",
    },
    "GD-B3-01": {
        "name": "Gas Detector B3-01", "class": "sensor", "zone_id": "Bay3",
        "last_serviced_daysago": 5, "status_nominal": "active",
        "criticality": "critical",
    },
    "GD-B3-02": {
        "name": "Gas Detector B3-02", "class": "sensor", "zone_id": "Bay3",
        "last_serviced_daysago": 180, "status_nominal": "degraded",  # dead sensor demo
        "criticality": "critical",
    },
    "PRV-22": {
        "name": "Pressure Relief Valve PRV-22", "class": "safety_valve", "zone_id": "Bay4",
        "last_serviced_daysago": 47, "status_nominal": "overdue_calibration",
        "criticality": "critical",
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# STATE MANAGER — live simulation state
# ──────────────────────────────────────────────────────────────────────────────

class FactoryStateManager:
    """Maintains in-memory factory simulation state across all 5 bays, updated by the event bus and periodic anomaly simulation."""

    def __init__(self) -> None:
        self._t0 = time.time()
        self.zone_overrides: dict[str, dict[str, Any]] = {}
        self.sensor_overrides: dict[str, dict[str, Any]] = {}
        self.scenario_active = False
        self.scenario_t = 0.0
        self.last_event_ts: dict[str, float] = {}  # equipment_id → unix ts of last reading
        
        # Periodic anomaly generator state
        self._tick = 0
        self._next_anomaly_tick = random.randint(5, 6)
        self._active_anomaly_bay: str | None = None
        self._anomaly_expires_tick: int = 0
        self._bays_sequence = ["Bay1", "Bay2", "Bay3", "Bay4", "Bay5"]
        self._bay_index = 0

    def apply_event(self, event: dict[str, Any]) -> None:
        """Update state from a simulator event."""
        zone_id = event.get("zone_id", "")
        source = event.get("source", "")
        severity = event.get("severity_hint", "normal")

        if zone_id:
            # Normalize zone ID format (Bay1 vs Bay 1)
            norm_zone = zone_id.replace(" ", "")
            if norm_zone not in self.zone_overrides:
                self.zone_overrides[norm_zone] = {}
            self.zone_overrides[norm_zone]["last_event"] = event
            self.zone_overrides[norm_zone]["last_severity"] = severity

        # Track last reading time for dead sensor detection
        eq_id = event.get("equipment_id", source)
        if eq_id:
            self.last_event_ts[eq_id] = time.time()

    def get_zone_risk_tier(self, zone_id: str) -> str:
        norm_zone = zone_id.replace(" ", "")
        override = self.zone_overrides.get(norm_zone, {})
        sev = override.get("last_severity", "normal")
        if sev == "critical":
            return "critical"
        elif sev == "elevated":
            return "high"
        return "low"

    def get_sensor_value(self, equipment_id: str, sensor_type: str, t: float, zone_id: str = "") -> float:
        """Simulate realistic sensor channel readings with natural noise and periodic correlated anomalies."""
        # Baseline values per sensor type / zone
        baselines = {
            "gas_ppm": 2.1,
            "temperature_c": 65.0,
            "pressure_bar": 11.2,
            "vibration_mms": 1.4,
            "flow_lmin": 340.0,
        }
        if sensor_type == "temperature_c":
            if "Bay3" in zone_id or equipment_id in ("C-14", "P-08"):
                baselines["temperature_c"] = 178.0
            elif "Bay2" in zone_id or equipment_id in ("HX-01"):
                baselines["temperature_c"] = 78.0
            elif "Bay1" in zone_id or equipment_id in ("T-07"):
                baselines["temperature_c"] = 85.0
        elif sensor_type == "pressure_bar":
            if "Bay4" in zone_id or equipment_id in ("R-22", "R-23"):
                baselines["pressure_bar"] = 15.1
            elif "Bay2" in zone_id or equipment_id in ("HX-01"):
                baselines["pressure_bar"] = 14.2
            elif "Bay3" in zone_id or equipment_id in ("C-14"):
                baselines["pressure_bar"] = 12.8

        base = baselines.get(sensor_type, 20.0)

        # Check for event override for this zone/sensor
        norm_zone = zone_id.replace(" ", "") if zone_id else ""
        if norm_zone:
            override = self.zone_overrides.get(norm_zone, {})
            if override.get("last_severity") in ("elevated", "critical"):
                event_evt = override.get("last_event", {})
                event_val = event_evt.get("value")
                evt_source = event_evt.get("source")
                if event_val is not None:
                    # Match source type
                    if (sensor_type == "gas_ppm" and evt_source == "gas_sensor") or \
                       (sensor_type in ("pressure_bar", "temperature_c") and evt_source == "scada"):
                        return float(event_val)

        # Natural continuous variance: sin wave drift + small Gaussian noise
        drift = math.sin(t / 60.0 + hash(equipment_id) % 10) * (base * 0.05) + random.gauss(0, max(base * 0.01, 0.05))
        return round(max(0.0, base + drift), 2)

    def is_sensor_dead(self, equipment_id: str) -> bool:
        """Sensor is 'dead' if no reading in >90s or explicitly degraded."""
        eq = EQUIPMENT_REGISTRY.get(equipment_id, {})
        if eq.get("status_nominal") == "degraded":
            return True
        last = self.last_event_ts.get(equipment_id, 0)
        return (time.time() - last) > 90 and last > 0

    def tick_simulation(self) -> None:
        """Advance periodic anomaly cycle across all bays."""
        self._tick += 1

        # Expire current anomaly if past duration
        if self._active_anomaly_bay and self._tick >= self._anomaly_expires_tick:
            bay = self._active_anomaly_bay
            self.zone_overrides[bay] = {"last_severity": "normal", "last_event": None}
            self._active_anomaly_bay = None

        # Trigger new correlated anomaly every 5-6 ticks
        if not self._active_anomaly_bay and self._tick >= self._next_anomaly_tick:
            target_bay = self._bays_sequence[self._bay_index % len(self._bays_sequence)]
            self._bay_index += 1
            self._active_anomaly_bay = target_bay
            self._anomaly_expires_tick = self._tick + random.randint(2, 3)  # Active for 2-3 ticks (~4-6s)
            self._next_anomaly_tick = self._tick + random.randint(5, 6)

            # Correlated anomaly parameters per bay
            anomalies = {
                "Bay1": {"source": "gas_sensor", "value": 45.2, "unit": "ppm", "severity_hint": "elevated", "permit": "PTW-0433 Active Tank Purging"},
                "Bay2": {"source": "scada", "value": 22.4, "unit": "bar", "severity_hint": "elevated", "maintenance": "HX-01 Gasket Inspection"},
                "Bay3": {"source": "gas_sensor", "value": 68.5, "unit": "ppm", "severity_hint": "elevated", "permit": "PTW-0441 Hot-Work Welding"},
                "Bay4": {"source": "scada", "value": 26.8, "unit": "bar", "severity_hint": "elevated", "maintenance": "PRV-22 Overdue Calibration"},
                "Bay5": {"source": "scada", "value": 118.5, "unit": "°C", "severity_hint": "elevated", "permit": "PTW-0430 High Pressure Finishing"},
            }

            anom_data = anomalies.get(target_bay, anomalies["Bay3"])
            event = {
                "event_id": f"anom_{self._tick}_{target_bay}",
                "source": anom_data["source"],
                "zone_id": target_bay,
                "equipment_id": "GD-B3-01" if target_bay == "Bay3" else ("C-14" if target_bay == "Bay3" else "T-07"),
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "value": anom_data["value"],
                "unit": anom_data["unit"],
                "severity_hint": anom_data["severity_hint"],
                "metadata": {
                    "permit": anom_data.get("permit"),
                    "maintenance": anom_data.get("maintenance"),
                }
            }

            self.zone_overrides[target_bay] = {
                "last_event": event,
                "last_severity": anom_data["severity_hint"],
            }


# Global state manager instance (shared across requests)
_state = FactoryStateManager()


def get_factory_state() -> FactoryStateManager:
    return _state


# ──────────────────────────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/zones")
async def get_zones() -> list[dict]:
    """Static zone layout for SVG heatmap rendering."""
    return ZONE_LAYOUT


@router.get("/state")
async def get_factory_state_endpoint() -> dict:
    """Live factory state across all 5 bays: zone risk tiers, sensor readings, telemetry."""
    # Advance periodic anomaly simulation tick
    _state.tick_simulation()

    t = time.time() - _state._t0

    zones = []
    for zone in ZONE_LAYOUT:
        zone_id = zone["zone_id"]
        tier = _state.get_zone_risk_tier(zone_id)
        override = _state.zone_overrides.get(zone_id, {})

        zones.append({
            "zone_id": zone_id,
            "label": zone["label"],
            "risk_tier": tier,
            "last_event": override.get("last_event"),
            "equipment_count": len(zone["equipment_ids"]),
        })

    sensors = []
    for eq_id, eq in EQUIPMENT_REGISTRY.items():
        if eq["class"] == "sensor":
            dead = _state.is_sensor_dead(eq_id)
            sensors.append({
                "sensor_id": eq_id,
                "name": eq["name"],
                "zone_id": eq["zone_id"],
                "type": "gas_detector",
                "value": None if dead else _state.get_sensor_value(eq_id, "gas_ppm", t, eq["zone_id"]),
                "unit": "ppm",
                "status": "dead" if dead else ("warning" if _state.get_zone_risk_tier(eq["zone_id"]) != "low" else "active"),
                "last_reading_ts": datetime.fromtimestamp(
                    _state.last_event_ts.get(eq_id, 0), tz=timezone.utc
                ).isoformat() if _state.last_event_ts.get(eq_id) else None,
            })

    # Detailed per-bay live telemetry streams for ALL 5 BAYS
    bays_telemetry = {}
    bay_configs = {
        "Bay1": ("T-07", "gas_ppm", "temperature_c", "pressure_bar"),
        "Bay2": ("HX-01", "gas_ppm", "temperature_c", "pressure_bar"),
        "Bay3": ("GD-B3-01", "gas_ppm", "temperature_c", "pressure_bar"),
        "Bay4": ("R-22", "gas_ppm", "temperature_c", "pressure_bar"),
        "Bay5": ("SEP-01", "gas_ppm", "temperature_c", "pressure_bar"),
    }

    for b_id, (eq, gas_t, temp_t, press_t) in bay_configs.items():
        gas_v = _state.get_sensor_value(eq, gas_t, t, b_id)
        temp_v = _state.get_sensor_value(eq, temp_t, t, b_id)
        press_v = _state.get_sensor_value(eq, press_t, t, b_id)

        bays_telemetry[b_id] = {
            "gas_concentration_ppm": gas_v,
            "temperature_c": temp_v,
            "pressure_bar": press_v,
            "gas_trend": "rising" if gas_v > 30 else "stable",
            "lel_percent": round(gas_v / 500.0, 2),
            "risk_tier": _state.get_zone_risk_tier(b_id),
        }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zones": zones,
        "sensors": sensors,
        "live_readings": bays_telemetry,
        "compound_risk_score": 0.65 if any(_state.get_zone_risk_tier(b) != "low" for b in bay_configs) else 0.12,
        "risk_level": "elevated" if any(_state.get_zone_risk_tier(b) != "low" for b in bay_configs) else "normal",
    }


@router.get("/equipment")
async def get_equipment_status() -> list[dict]:
    """Equipment status with health scores, maintenance dates, and alerts."""
    result = []

    for eq_id, eq in EQUIPMENT_REGISTRY.items():
        days_since_service = eq.get("last_serviced_daysago", 0)
        health = max(0, round(100 - (days_since_service * 0.8), 1))
        overdue = days_since_service > 30

        status = eq.get("status_nominal", "operational")
        dead = _state.is_sensor_dead(eq_id)
        if dead:
            status = "no_signal"

        alerts = []
        if overdue:
            alerts.append(f"Maintenance overdue by {int(days_since_service - 30)} days")
        if status == "overdue_calibration":
            alerts.append("Calibration overdue")
        if status == "degraded" or dead:
            alerts.append("No signal / offline")
        if status == "pending_repair":
            alerts.append("Repair scheduled")

        result.append({
            "equipment_id": eq_id,
            "name": eq["name"],
            "class": eq["class"],
            "zone_id": eq["zone_id"],
            "status": status,
            "criticality": eq.get("criticality", "medium"),
            "health_pct": health,
            "last_serviced_days_ago": days_since_service,
            "overdue_maintenance": overdue,
            "alerts": alerts,
        })

    return result


@router.get("/kpis")
async def get_production_kpis() -> dict:
    """Production KPIs derived from live simulation state."""
    t = time.time() - _state._t0
    production_rate = round(847 + math.sin(t / 300) * 23 + random.gauss(0, 2), 1)
    efficiency = round(91.4 + math.sin(t / 400) * 2.1 + random.gauss(0, 0.3), 1)
    power_kw = round(2840 + math.sin(t / 200) * 80 + random.gauss(0, 5), 0)
    active_alarms = sum(
        1 for z in _state.zone_overrides.values()
        if z.get("last_severity") in ("elevated", "critical")
    )
    personnel = {
        "Bay1": 3, "Bay2": 4, "Bay3": 7, "Bay4": 5, "Bay5": 8,
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "production_rate_units_hr": production_rate,
        "plant_efficiency_pct": efficiency,
        "power_draw_kw": power_kw,
        "active_alarms": active_alarms,
        "active_permits": await _get_active_permits_count(),
        "personnel_onsite": sum(personnel.values()),
        "personnel_by_zone": personnel,
        "mtbi_hours": 2847,
        "last_incident_days_ago": 7,
        "shifts": {
            "current": "Day Shift — 06:00–14:00",
            "supervisor": "Rajesh Mehta",
            "changeover_in_min": 22,
        },
    }


async def _get_active_permits_count() -> int:
    import os
    from backend.db.db import get_db
    db_path = os.environ.get("SQLITE_PATH", "./vigil.db")
    try:
        async with get_db(db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) as cnt FROM permits WHERE status = 'active'")
            row = await cursor.fetchone()
            return row["cnt"] if row else 0
    except Exception:
        return 0


@router.get("/permits")
async def get_active_permits() -> list[dict]:
    """Return all persisted permits-to-work from the SQLite database."""
    import os
    from backend.db.db import get_db
    db_path = os.environ.get("SQLITE_PATH", "./vigil.db")
    try:
        async with get_db(db_path) as db:
            cursor = await db.execute(
                """
                SELECT permit_id, permit_type, zone_id, holder as issued_to, status,
                       window_start as issued_at, window_end as expires_at
                  FROM permits
                ORDER BY CASE WHEN status = 'active' THEN 0 ELSE 1 END, permit_id
                """
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
