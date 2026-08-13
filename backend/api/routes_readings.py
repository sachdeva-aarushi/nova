"""backend/api/routes_readings.py — Endpoints for sensor readings and pending permits."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api", tags=["readings"])

DB_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = DB_DIR / "vigil.db"


def _get_db_path() -> str:
    return os.environ.get("SQLITE_DB_PATH", os.environ.get("SQLITE_PATH", str(DEFAULT_DB_PATH)))


@router.get("/readings/latest")
async def get_latest_readings() -> dict[str, dict[str, Any]]:
    """Return the most recent reading per zone per sensor type from SQLite."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
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


@router.get("/readings/history")
async def get_readings_history(
    zone_id: str = Query("Z-03"),
    sensor_type: str = Query("gas_lel"),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Return the last N real readings for a zone and sensor type."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, ts, zone_id, sensor_type, value, unit, is_anomaly, cycle_num
            FROM sensor_readings
            WHERE zone_id = ? AND sensor_type = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (zone_id, sensor_type, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/permits/pending")
async def get_pending_permits(case_id: str | None = Query(None)) -> list[dict[str, Any]]:
    """Return all pending permit proposals."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if case_id:
            rows = conn.execute(
                "SELECT * FROM pending_permits WHERE status = 'pending' AND case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pending_permits WHERE status = 'pending' ORDER BY created_at DESC",
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/permits/{permit_id}")
async def get_permit_by_id(permit_id: str) -> dict[str, Any]:
    """Return a single permit row by ID."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM pending_permits WHERE id = ?", (permit_id,)).fetchone()
        if not row:
            row = conn.execute("SELECT * FROM permits WHERE permit_id = ?", (permit_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Permit not found")
        return dict(row)
    finally:
        conn.close()
