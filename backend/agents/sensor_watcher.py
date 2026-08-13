"""
backend/agents/sensor_watcher.py — SensorWatcher agent for 10-second polling loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = DB_DIR / "vigil.db"


class SensorWatcher:
    """Polls sensor_readings table on a 10-second loop."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.environ.get("SQLITE_DB_PATH", str(DEFAULT_DB_PATH))

    async def get_latest_readings(self) -> dict[str, dict[str, Any]]:
        """Pull the most recent reading per zone per sensor type from SQLite."""
        def _sync_query() -> dict[str, dict[str, Any]]:
            conn = sqlite3.connect(self.db_path)
            try:
                rows = conn.execute("""
                    SELECT zone_id, sensor_type, value, unit, ts
                    FROM sensor_readings sr1
                    WHERE ts = (
                        SELECT MAX(ts) FROM sensor_readings sr2
                        WHERE sr2.zone_id = sr1.zone_id
                          AND sr2.sensor_type = sr1.sensor_type
                    )
                    ORDER BY zone_id, sensor_type
                """).fetchall()

                readings: dict[str, dict[str, Any]] = {}
                for row in rows:
                    zone, sensor, value, unit, ts = row
                    if zone not in readings:
                        readings[zone] = {}
                    readings[zone][sensor] = {"value": value, "unit": unit, "ts": ts}

                return readings
            finally:
                conn.close()

        return await asyncio.to_thread(_sync_query)
