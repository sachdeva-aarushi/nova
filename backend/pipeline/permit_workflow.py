"""
PermitWorkflow — triggered when anomaly is confirmed by Gemini Flash.
Uses Groq to generate a specific permit action recommendation.
Writes the pending permit to SQLite.
Broadcasts the permit proposal to UI.
Does NOT auto-execute anything — human must accept or reject.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.services.groq_client import chat_json
from backend.services.sensor_generator import SENSOR_CONFIG

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = DB_DIR / "vigil.db"


class PermitWorkflow:
    PERMIT_PROMPT = """
You are NOVA's safety action engine. An anomaly has been confirmed.

ANOMALY DETAILS:
{anomaly_details}

ZONE: {zone_id}
SENSOR: {sensor_type}
READING: {value} {unit} (threshold: {threshold})
SEVERITY: {severity}

ACTIVE CONTEXT (from DB):
- Active permits in this zone: {active_permits}
- Recent maintenance: {recent_maintenance}
- Current shift: {current_shift}

HISTORICAL PRECEDENT (from Qdrant lessons_learned):
{historical_lessons}

Based on this data, determine the single most important safety action needed RIGHT NOW. Choose from:
- close_gas_pipeline (if gas LEL is high)
- suspend_hotwork_permit (if hot work is active near gas anomaly)
- evacuate_zone (if critical threshold crossed)
- increase_ventilation (if gas is elevated but not yet critical)
- shutdown_equipment (if pressure or temp anomaly)

Respond in JSON only:
{{
    "action_type": "close_gas_pipeline | suspend_hotwork_permit | evacuate_zone | increase_ventilation | shutdown_equipment",
    "permit_id": "PRM-XXXX",
    "reason": "one clear sentence explaining why this action is needed",
    "urgency": "immediate | within_5_min | monitoring",
    "voice_announcement": "what NOVA should say to the operator — direct, under 2 sentences, cite the actual reading",
    "acceptance_phrase": "what the operator should say to accept",
    "rejection_phrase": "what the operator should say to reject"
}}
"""

    def __init__(
        self,
        db_path: str | None = None,
        ws_manager: Any = None,
        voice_agent: Any = None,
    ) -> None:
        self.db_path = db_path or os.environ.get("SQLITE_DB_PATH", str(DEFAULT_DB_PATH))
        self.ws_manager = ws_manager
        self.voice_agent = voice_agent

    async def generate_permit(self, anomaly: dict[str, Any], case_id: str | None = None) -> dict[str, Any]:
        cid = case_id or f"case_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
        zone_id = anomaly.get("zone_id", "Z-03")
        sensor_type = anomaly.get("sensor_type", "gas_lel")
        value = anomaly.get("value", 18.0)
        unit = anomaly.get("unit", "%LEL")
        severity = anomaly.get("severity", anomaly.get("severity_hint", "high"))

        # 1. Pull context from DB
        active_permits = await self._get_active_permits(zone_id)
        recent_maintenance = await self._get_recent_maintenance(zone_id)
        current_shift = await self._get_current_shift()

        # 2. Pull lessons from Qdrant if available
        historical_lessons: list[dict] = []
        try:
            from backend.services.qdrant_client import retrieve_context
            q_res = await retrieve_context(f"{sensor_type} anomaly {zone_id}")
            historical_lessons = q_res.get("lessons_learned", [])
        except Exception:
            historical_lessons = []

        cfg = SENSOR_CONFIG.get(sensor_type, {"warn_threshold": 10.0})
        threshold = cfg.get("warn_threshold", 10.0)

        prompt = self.PERMIT_PROMPT.format(
            anomaly_details=json.dumps(anomaly, indent=2),
            zone_id=zone_id,
            sensor_type=sensor_type,
            value=value,
            unit=unit,
            threshold=threshold,
            severity=severity,
            active_permits=json.dumps(active_permits, indent=2),
            recent_maintenance=json.dumps(recent_maintenance, indent=2),
            current_shift=json.dumps(current_shift, indent=2),
            historical_lessons=json.dumps(historical_lessons, indent=2),
        )

        try:
            permit_data = await chat_json("You respond strictly in valid JSON.", prompt)
        except Exception as exc:
            logger.warning("Groq chat_json failed, using fallback permit generation: %s", exc)
            permit_data = {
                "action_type": "suspend_hotwork_permit" if "gas" in sensor_type else "shutdown_equipment",
                "permit_id": f"PRM-{random.randint(1000, 9999)}",
                "reason": f"Elevated {sensor_type} reading of {value} {unit} in {zone_id} exceeds safe baseline threshold.",
                "urgency": "immediate",
                "voice_announcement": f"Attention supervisor: {sensor_type} reading in {zone_id} reached {value} {unit}. Recommend immediate action.",
                "acceptance_phrase": "yes close it",
                "rejection_phrase": "reject",
            }

        permit_id = permit_data.get("permit_id", f"PRM-{random.randint(1000, 9999)}")
        action_type = permit_data.get("action_type", "close_gas_pipeline")
        reason = permit_data.get("reason", f"Anomaly detected in {zone_id}")

        # 3. Write to pending_permits table
        await self._insert_pending_permit({
            "id": permit_id,
            "case_id": cid,
            "zone_id": zone_id,
            "action_type": action_type,
            "reason": reason,
            "status": "pending",
        })

        # 4. Broadcast to UI
        if self.ws_manager:
            try:
                await self.ws_manager.broadcast({
                    "type": "permit.proposed",
                    "payload": {
                        "permit_id": permit_id,
                        "case_id": cid,
                        "zone_id": zone_id,
                        "action_type": action_type,
                        "reason": reason,
                        "urgency": permit_data.get("urgency", "immediate"),
                        "voice_announcement": permit_data.get("voice_announcement", ""),
                        "acceptance_phrase": permit_data.get("acceptance_phrase", "yes close it"),
                        "rejection_phrase": permit_data.get("rejection_phrase", "reject"),
                    },
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as err:
                logger.debug("WS broadcast permit.proposed error: %s", err)

        # 5. Optional voice announcement
        if self.voice_agent and hasattr(self.voice_agent, "speak"):
            try:
                await self.voice_agent.speak(
                    text=permit_data.get("voice_announcement", ""),
                    case_id=cid,
                )
            except Exception as err:
                logger.debug("Voice agent speak error: %s", err)

        return permit_data

    async def _get_active_permits(self, zone_id: str) -> list[dict[str, Any]]:
        def _query() -> list[dict[str, Any]]:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT * FROM permits WHERE (zone_id = ? OR zone_id LIKE ?) AND status = 'active'",
                    (zone_id, f"%{zone_id}%"),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        return await asyncio.to_thread(_query)

    async def _get_recent_maintenance(self, zone_id: str) -> list[dict[str, Any]]:
        def _query() -> list[dict[str, Any]]:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT * FROM maintenance_records WHERE (zone_id = ? OR zone_id LIKE ?) ORDER BY record_id DESC LIMIT 5",
                    (zone_id, f"%{zone_id}%"),
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                return []
            finally:
                conn.close()
        return await asyncio.to_thread(_query)

    async def _get_current_shift(self) -> dict[str, Any]:
        def _query() -> dict[str, Any]:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute("SELECT * FROM shifts ORDER BY shift_id DESC LIMIT 1").fetchone()
                return dict(row) if row else {"shift": "Day Shift — 06:00-14:00", "supervisor": "Rajesh Mehta"}
            except Exception:
                return {"shift": "Day Shift — 06:00-14:00", "supervisor": "Rajesh Mehta"}
            finally:
                conn.close()
        return await asyncio.to_thread(_query)

    async def _insert_pending_permit(self, data: dict[str, Any]) -> None:
        def _query() -> None:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO pending_permits
                        (id, case_id, zone_id, action_type, reason, status, created_at)
                    VALUES
                        (:id, :case_id, :zone_id, :action_type, :reason, :status, datetime('now', 'utc'))
                """, data)
                conn.commit()
            finally:
                conn.close()
        await asyncio.to_thread(_query)
