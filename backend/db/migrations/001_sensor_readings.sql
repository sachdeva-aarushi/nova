CREATE TABLE IF NOT EXISTS sensor_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          DATETIME DEFAULT (datetime('now', 'utc')),
    zone_id     TEXT NOT NULL,
    sensor_type TEXT NOT NULL,   -- 'gas_lel', 'pressure_bar', 'temp_c', 'flow_lpm'
    value       REAL NOT NULL,
    unit        TEXT NOT NULL,
    is_anomaly  INTEGER DEFAULT 0,  -- 1 if this reading was an injected spike
    cycle_num   INTEGER NOT NULL    -- which generation cycle produced this
);

CREATE INDEX IF NOT EXISTS idx_readings_zone_ts
    ON sensor_readings(zone_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_readings_ts
    ON sensor_readings(ts DESC);

CREATE TABLE IF NOT EXISTS pending_permits (
    id              TEXT PRIMARY KEY,  -- permit ID e.g. "PRM-0042"
    case_id         TEXT NOT NULL,
    zone_id         TEXT NOT NULL,
    action_type     TEXT NOT NULL,  -- 'close_gas_pipeline', 'suspend_hotwork', etc.
    reason          TEXT NOT NULL,  -- LLM-generated reason
    status          TEXT DEFAULT 'pending',  -- pending | accepted | rejected
    created_at      DATETIME DEFAULT (datetime('now', 'utc')),
    resolved_at     DATETIME,
    resolved_by     TEXT,           -- 'operator_voice_command' | 'operator_ui'
    operator_command TEXT           -- exact words the operator used
);
