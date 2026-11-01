-- ============================================================================
-- Road Hazard Robot Fleet Operations - PostgreSQL PL/pgSQL Stored Logic
-- File: 02_procedures_plpgsql.sql
-- ============================================================================

-- Function: Haversine distance in meters
CREATE OR REPLACE FUNCTION fn_haversine_distance(
    lat1 DOUBLE PRECISION,
    lon1 DOUBLE PRECISION,
    lat2 DOUBLE PRECISION,
    lon2 DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    r CONSTANT DOUBLE PRECISION := 6371000.0;
    dlat DOUBLE PRECISION;
    dlon DOUBLE PRECISION;
    a DOUBLE PRECISION;
    c DOUBLE PRECISION;
BEGIN
    dlat := radians(lat2 - lat1);
    dlon := radians(lon2 - lon1);
    a := sin(dlat / 2.0)^2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2.0)^2;
    IF a > 1.0 THEN
        a := 1.0;
    END IF;
    c := 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
    RETURN round((r * c)::NUMERIC, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function: Calculate cluster count within radius
CREATE OR REPLACE FUNCTION fn_calculate_cluster(
    p_lat DOUBLE PRECISION,
    p_lon DOUBLE PRECISION,
    p_hazard_class VARCHAR,
    p_radius_m DOUBLE PRECISION DEFAULT 15.0
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 1;
    r RECORD;
BEGIN
    FOR r IN
        SELECT latitude, longitude
        FROM hazards
        WHERE LOWER(hazard_class) = LOWER(p_hazard_class)
          AND created_at >= (NOW() AT TIME ZONE 'utc' - INTERVAL '24 hours')
    LOOP
        IF fn_haversine_distance(p_lat, p_lon, r.latitude, r.longitude) <= p_radius_m THEN
            v_count := v_count + 1;
        END IF;
    END LOOP;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Calculate severity score
CREATE OR REPLACE FUNCTION fn_calculate_severity(
    p_hazard_class VARCHAR,
    p_confidence DOUBLE PRECISION,
    p_cluster_count INTEGER DEFAULT 1
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    v_base DOUBLE PRECISION;
    v_mult DOUBLE PRECISION;
    v_score DOUBLE PRECISION;
BEGIN
    CASE LOWER(p_hazard_class)
        WHEN 'pothole' THEN v_base := 80.0;
        WHEN 'crack'   THEN v_base := 60.0;
        WHEN 'animal'  THEN v_base := 90.0;
        ELSE v_base := 50.0;
    END CASE;

    v_mult := LEAST(1.0 + (p_cluster_count - 1) * 0.15, 2.0);
    v_score := v_base * p_confidence * v_mult;
    RETURN round(LEAST(100.0, v_score)::NUMERIC, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger Function: Auto update updated_at
CREATE OR REPLACE FUNCTION trg_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := (NOW() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_hazards_updated ON hazards;
CREATE TRIGGER trg_hazards_updated
BEFORE UPDATE ON hazards
FOR EACH ROW
EXECUTE FUNCTION trg_set_updated_at();

-- Stored Procedure: Insert Hazard
CREATE OR REPLACE PROCEDURE sp_insert_hazard(
    IN p_robot_id VARCHAR,
    IN p_hazard_class VARCHAR,
    IN p_confidence DOUBLE PRECISION,
    IN p_latitude DOUBLE PRECISION,
    IN p_longitude DOUBLE PRECISION,
    IN p_bbox_x1 DOUBLE PRECISION,
    IN p_bbox_y1 DOUBLE PRECISION,
    IN p_bbox_x2 DOUBLE PRECISION,
    IN p_bbox_y2 DOUBLE PRECISION,
    IN p_snapshot_path VARCHAR,
    IN p_reported_by VARCHAR,
    OUT o_hazard_id INTEGER,
    OUT o_severity_score DOUBLE PRECISION,
    OUT o_cluster_count INTEGER
) AS $$
BEGIN
    o_cluster_count := fn_calculate_cluster(p_latitude, p_longitude, p_hazard_class);
    o_severity_score := fn_calculate_severity(p_hazard_class, p_confidence, o_cluster_count);

    INSERT INTO hazards (
        robot_id, hazard_class, confidence, latitude, longitude,
        bbox_x1, bbox_y1, bbox_x2, bbox_y2, snapshot_path,
        severity_score, cluster_count, status, reported_by,
        created_at, updated_at
    ) VALUES (
        p_robot_id, LOWER(p_hazard_class), p_confidence, p_latitude, p_longitude,
        p_bbox_x1, p_bbox_y1, p_bbox_x2, p_bbox_y2, p_snapshot_path,
        o_severity_score, o_cluster_count, 'new', p_reported_by,
        (NOW() AT TIME ZONE 'utc'), (NOW() AT TIME ZONE 'utc')
    )
    RETURNING id INTO o_hazard_id;
END;
$$ LANGUAGE plpgsql;

-- Stored Procedure: Update Hazard Status
CREATE OR REPLACE PROCEDURE sp_update_hazard_status(
    IN p_hazard_id INTEGER,
    IN p_new_status VARCHAR,
    IN p_user_role VARCHAR
) AS $$
DECLARE
    v_status VARCHAR;
BEGIN
    v_status := LOWER(p_new_status);
    IF v_status NOT IN ('new', 'acknowledged', 'repaired') THEN
        RAISE EXCEPTION 'Invalid status: %. Must be new, acknowledged, or repaired.', p_new_status;
    END IF;

    IF v_status = 'repaired' AND LOWER(p_user_role) != 'admin' THEN
        RAISE EXCEPTION 'Unauthorized: Only admins can mark hazards as repaired.';
    END IF;

    UPDATE hazards
    SET status = v_status,
        updated_at = (NOW() AT TIME ZONE 'utc')
    WHERE id = p_hazard_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Hazard not found with id: %', p_hazard_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Stored Procedure: Record Robot Heartbeat
CREATE OR REPLACE PROCEDURE sp_record_heartbeat(
    IN p_robot_id VARCHAR,
    IN p_status VARCHAR,
    IN p_battery DOUBLE PRECISION,
    IN p_latitude DOUBLE PRECISION,
    IN p_longitude DOUBLE PRECISION,
    IN p_speed DOUBLE PRECISION,
    IN p_ip_address VARCHAR
) AS $$
BEGIN
    INSERT INTO robot_status (
        robot_id, status, battery_percentage, current_latitude, current_longitude,
        speed, ip_address, last_seen
    ) VALUES (
        p_robot_id, LOWER(p_status), p_battery, p_latitude, p_longitude,
        p_speed, p_ip_address, (NOW() AT TIME ZONE 'utc')
    )
    ON CONFLICT (robot_id) DO UPDATE SET
        status = EXCLUDED.status,
        battery_percentage = EXCLUDED.battery_percentage,
        current_latitude = COALESCE(EXCLUDED.current_latitude, robot_status.current_latitude),
        current_longitude = COALESCE(EXCLUDED.current_longitude, robot_status.current_longitude),
        speed = EXCLUDED.speed,
        ip_address = COALESCE(EXCLUDED.ip_address, robot_status.ip_address),
        last_seen = EXCLUDED.last_seen;
END;
$$ LANGUAGE plpgsql;

