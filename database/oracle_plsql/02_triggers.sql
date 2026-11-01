-- ============================================================================
-- Road Hazard Robot Fleet Operations - Oracle PL/SQL Triggers
-- File: 02_triggers.sql
-- ============================================================================

-- Trigger: Auto-populate primary key for hazards
CREATE OR REPLACE TRIGGER trg_hazards_bi_id
BEFORE INSERT ON hazards
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT hazard_id_seq.NEXTVAL INTO :NEW.id FROM dual;
    END IF;
    IF :NEW.created_at IS NULL THEN
        :NEW.created_at := SYSTIMESTAMP;
    END IF;
    IF :NEW.updated_at IS NULL THEN
        :NEW.updated_at := SYSTIMESTAMP;
    END IF;
END;
/

-- Trigger: Automatically refresh updated_at on hazard modification
CREATE OR REPLACE TRIGGER trg_hazards_bu_timestamp
BEFORE UPDATE ON hazards
FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

-- Trigger: Auto-populate primary key for users
CREATE OR REPLACE TRIGGER trg_users_bi_id
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT user_id_seq.NEXTVAL INTO :NEW.id FROM dual;
    END IF;
    IF :NEW.created_at IS NULL THEN
        :NEW.created_at := SYSTIMESTAMP;
    END IF;
END;
/

-- Trigger: Auto-populate primary key for alert_logs
CREATE OR REPLACE TRIGGER trg_alert_logs_bi_id
BEFORE INSERT ON alert_logs
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT alert_log_id_seq.NEXTVAL INTO :NEW.id FROM dual;
    END IF;
    IF :NEW.sent_at IS NULL THEN
        :NEW.sent_at := SYSTIMESTAMP;
    END IF;
END;
/

-- Trigger: Auto-populate primary key for offline_events
CREATE OR REPLACE TRIGGER trg_offline_events_bi_id
BEFORE INSERT ON offline_events
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT offline_event_id_seq.NEXTVAL INTO :NEW.id FROM dual;
    END IF;
    IF :NEW.created_at IS NULL THEN
        :NEW.created_at := SYSTIMESTAMP;
    END IF;
END;
/

-- Trigger: Automatically refresh last_seen on robot_status modification
CREATE OR REPLACE TRIGGER trg_robot_status_bu_last_seen
BEFORE UPDATE ON robot_status
FOR EACH ROW
BEGIN
    :NEW.last_seen := SYSTIMESTAMP;
END;
/

