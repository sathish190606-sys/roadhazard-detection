-- ============================================================================
-- Road Hazard Robot Fleet Operations - PostgreSQL PL/pgSQL Database Schema
-- File: 01_schema_plpgsql.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS hazards (
    id SERIAL PRIMARY KEY,
    robot_id VARCHAR(50) NOT NULL,
    hazard_class VARCHAR(20) NOT NULL CHECK (hazard_class IN ('pothole', 'crack', 'animal', 'debris', 'obstacle')),
    confidence DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    bbox_x1 DOUBLE PRECISION,
    bbox_y1 DOUBLE PRECISION,
    bbox_x2 DOUBLE PRECISION,
    bbox_y2 DOUBLE PRECISION,
    snapshot_path VARCHAR(255),
    repair_snapshot_path VARCHAR(255),
    severity_score DOUBLE PRECISION DEFAULT 50.0 NOT NULL,
    cluster_count INTEGER DEFAULT 1 NOT NULL,
    status VARCHAR(20) DEFAULT 'new' NOT NULL CHECK (status IN ('new', 'acknowledged', 'repaired')),
    reported_by VARCHAR(50),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pg_hazards_robot_id ON hazards(robot_id);
CREATE INDEX IF NOT EXISTS idx_pg_hazards_class ON hazards(hazard_class);
CREATE INDEX IF NOT EXISTS idx_pg_hazards_status ON hazards(status);
CREATE INDEX IF NOT EXISTS idx_pg_hazards_severity ON hazards(severity_score);
CREATE INDEX IF NOT EXISTS idx_pg_hazards_geo ON hazards(latitude, longitude);

CREATE TABLE IF NOT EXISTS robot_status (
    robot_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'offline' NOT NULL CHECK (status IN ('online', 'offline', 'patrol', 'emergency_stop')),
    battery_percentage DOUBLE PRECISION DEFAULT 100.0 NOT NULL,
    current_latitude DOUBLE PRECISION,
    current_longitude DOUBLE PRECISION,
    speed DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    ip_address VARCHAR(50),
    last_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'viewer' NOT NULL CHECK (role IN ('admin', 'viewer', 'operator')),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_logs (
    id SERIAL PRIMARY KEY,
    hazard_id INTEGER NOT NULL REFERENCES hazards(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('email', 'sms', 'webhook')),
    recipient VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'sent' NOT NULL CHECK (status IN ('sent', 'failed', 'rate_limited')),
    message TEXT,
    sent_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL
);

CREATE TABLE IF NOT EXISTS offline_events (
    id SERIAL PRIMARY KEY,
    seq INTEGER,
    payload_json TEXT NOT NULL,
    synced INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc') NOT NULL
);

