-- ============================================================================
-- Road Hazard Robot Fleet Operations - Oracle PL/SQL Database Schema
-- File: 01_schema.sql
-- ============================================================================

-- Clean up existing objects if re-running
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE alert_logs CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE hazards CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE robot_status CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE users CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE offline_events CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- Sequences for Primary Keys
BEGIN
    EXECUTE IMMEDIATE 'DROP SEQUENCE hazard_id_seq';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
CREATE SEQUENCE hazard_id_seq START WITH 1 INCREMENT BY 1 NOCACHE;

BEGIN
    EXECUTE IMMEDIATE 'DROP SEQUENCE user_id_seq';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
CREATE SEQUENCE user_id_seq START WITH 1 INCREMENT BY 1 NOCACHE;

BEGIN
    EXECUTE IMMEDIATE 'DROP SEQUENCE alert_log_id_seq';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
CREATE SEQUENCE alert_log_id_seq START WITH 1 INCREMENT BY 1 NOCACHE;

BEGIN
    EXECUTE IMMEDIATE 'DROP SEQUENCE offline_event_id_seq';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
CREATE SEQUENCE offline_event_id_seq START WITH 1 INCREMENT BY 1 NOCACHE;

-- 1. Hazards Table
CREATE TABLE hazards (
    id                    NUMBER(12) NOT NULL,
    robot_id              VARCHAR2(50) NOT NULL,
    hazard_class          VARCHAR2(20) NOT NULL,
    confidence            NUMBER(5, 4) NOT NULL,
    latitude              NUMBER(10, 7) NOT NULL,
    longitude             NUMBER(10, 7) NOT NULL,
    bbox_x1               NUMBER(10, 2),
    bbox_y1               NUMBER(10, 2),
    bbox_x2               NUMBER(10, 2),
    bbox_y2               NUMBER(10, 2),
    snapshot_path         VARCHAR2(255),
    repair_snapshot_path  VARCHAR2(255),
    severity_score        NUMBER(6, 2) DEFAULT 50.0 NOT NULL,
    cluster_count         NUMBER(6) DEFAULT 1 NOT NULL,
    status                VARCHAR2(20) DEFAULT 'new' NOT NULL,
    reported_by           VARCHAR2(50),
    created_at            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_hazards PRIMARY KEY (id),
    CONSTRAINT chk_hazard_class CHECK (hazard_class IN ('pothole', 'crack', 'animal', 'debris', 'obstacle')),
    CONSTRAINT chk_hazard_status CHECK (status IN ('new', 'acknowledged', 'repaired'))
);

CREATE INDEX idx_hazards_robot_id ON hazards (robot_id);
CREATE INDEX idx_hazards_class ON hazards (hazard_class);
CREATE INDEX idx_hazards_status ON hazards (status);
CREATE INDEX idx_hazards_severity ON hazards (severity_score);
CREATE INDEX idx_hazards_geo ON hazards (latitude, longitude);
CREATE INDEX idx_hazards_created_at ON hazards (created_at);

-- 2. Robot Status Table (Fleet Telemetry)
CREATE TABLE robot_status (
    robot_id              VARCHAR2(50) NOT NULL,
    status                VARCHAR2(20) DEFAULT 'offline' NOT NULL,
    battery_percentage    NUMBER(5, 2) DEFAULT 100.0 NOT NULL,
    current_latitude      NUMBER(10, 7),
    current_longitude     NUMBER(10, 7),
    speed                 NUMBER(5, 2) DEFAULT 0.0 NOT NULL,
    ip_address            VARCHAR2(50),
    last_seen             TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_robot_status PRIMARY KEY (robot_id),
    CONSTRAINT chk_robot_status CHECK (status IN ('online', 'offline', 'patrol', 'emergency_stop'))
);

CREATE INDEX idx_robot_status_last_seen ON robot_status (last_seen);

-- 3. Users Table (Authentication and Authorization)
CREATE TABLE users (
    id                    NUMBER(12) NOT NULL,
    username              VARCHAR2(50) NOT NULL,
    hashed_password       VARCHAR2(255) NOT NULL,
    role                  VARCHAR2(20) DEFAULT 'viewer' NOT NULL,
    is_active             NUMBER(1) DEFAULT 1 NOT NULL,
    created_at            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT chk_users_role CHECK (role IN ('admin', 'viewer', 'operator')),
    CONSTRAINT chk_users_is_active CHECK (is_active IN (0, 1))
);

CREATE INDEX idx_users_username ON users (username);

-- 4. Alert Logs Table
CREATE TABLE alert_logs (
    id                    NUMBER(12) NOT NULL,
    hazard_id             NUMBER(12) NOT NULL,
    channel               VARCHAR2(20) NOT NULL,
    recipient             VARCHAR2(100) NOT NULL,
    status                VARCHAR2(20) DEFAULT 'sent' NOT NULL,
    message               CLOB,
    sent_at               TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_alert_logs PRIMARY KEY (id),
    CONSTRAINT fk_alert_logs_hazard FOREIGN KEY (hazard_id) REFERENCES hazards(id) ON DELETE CASCADE,
    CONSTRAINT chk_alert_channel CHECK (channel IN ('email', 'sms', 'webhook')),
    CONSTRAINT chk_alert_status CHECK (status IN ('sent', 'failed', 'rate_limited'))
);

CREATE INDEX idx_alert_logs_hazard_id ON alert_logs (hazard_id);
CREATE INDEX idx_alert_logs_sent_at ON alert_logs (sent_at);

-- 5. Offline Events Table (Local/Gateway Sync Buffer)
CREATE TABLE offline_events (
    id                    NUMBER(12) NOT NULL,
    seq                   NUMBER(12),
    payload_json          CLOB NOT NULL,
    synced                NUMBER(1) DEFAULT 0 NOT NULL,
    created_at            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_offline_events PRIMARY KEY (id),
    CONSTRAINT chk_offline_synced CHECK (synced IN (0, 1))
);

CREATE INDEX idx_offline_events_synced ON offline_events (synced);

