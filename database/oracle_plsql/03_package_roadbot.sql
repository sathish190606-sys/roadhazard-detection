-- ============================================================================
-- Road Hazard Robot Fleet Operations - Oracle PL/SQL Package
-- Package: PKG_ROADBOT
-- File: 03_package_roadbot.sql
-- ============================================================================

CREATE OR REPLACE PACKAGE pkg_roadbot AS
    -- Constants
    c_earth_radius_m  CONSTANT NUMBER := 6371000;
    c_pi              CONSTANT NUMBER := 3.14159265358979323846;

    -- Custom Exceptions
    e_unauthorized_repair EXCEPTION;
    PRAGMA EXCEPTION_INIT(e_unauthorized_repair, -20001);

    e_invalid_hazard_status EXCEPTION;
    PRAGMA EXCEPTION_INIT(e_invalid_hazard_status, -20002);

    -- Functions
    FUNCTION fn_deg_to_rad(p_deg IN NUMBER) RETURN NUMBER;

    FUNCTION fn_haversine_distance(
        p_lat1 IN NUMBER,
        p_lon1 IN NUMBER,
        p_lat2 IN NUMBER,
        p_lon2 IN NUMBER
    ) RETURN NUMBER;

    FUNCTION fn_calculate_cluster(
        p_lat          IN NUMBER,
        p_lon          IN NUMBER,
        p_hazard_class IN VARCHAR2,
        p_radius_m     IN NUMBER DEFAULT 15.0
    ) RETURN NUMBER;

    FUNCTION fn_calculate_severity(
        p_hazard_class  IN VARCHAR2,
        p_confidence    IN NUMBER,
        p_cluster_count IN NUMBER DEFAULT 1
    ) RETURN NUMBER;

    -- Stored Procedures
    PROCEDURE sp_insert_hazard(
        p_robot_id             IN VARCHAR2,
        p_hazard_class         IN VARCHAR2,
        p_confidence           IN NUMBER,
        p_latitude             IN NUMBER,
        p_longitude            IN NUMBER,
        p_bbox_x1              IN NUMBER DEFAULT NULL,
        p_bbox_y1              IN NUMBER DEFAULT NULL,
        p_bbox_x2              IN NUMBER DEFAULT NULL,
        p_bbox_y2              IN NUMBER DEFAULT NULL,
        p_snapshot_path        IN VARCHAR2 DEFAULT NULL,
        p_reported_by          IN VARCHAR2 DEFAULT NULL,
        o_hazard_id            OUT NUMBER,
        o_severity_score       OUT NUMBER,
        o_cluster_count        OUT NUMBER
    );

    PROCEDURE sp_update_hazard_status(
        p_hazard_id     IN NUMBER,
        p_new_status    IN VARCHAR2,
        p_user_role     IN VARCHAR2 DEFAULT 'admin',
        o_updated_at    OUT TIMESTAMP
    );

    PROCEDURE sp_record_heartbeat(
        p_robot_id           IN VARCHAR2,
        p_status             IN VARCHAR2,
        p_battery_percentage IN NUMBER,
        p_latitude           IN NUMBER DEFAULT NULL,
        p_longitude          IN NUMBER DEFAULT NULL,
        p_speed              IN NUMBER DEFAULT 0.0,
        p_ip_address         IN VARCHAR2 DEFAULT NULL
    );

    PROCEDURE sp_log_alert(
        p_hazard_id  IN NUMBER,
        p_channel    IN VARCHAR2,
        p_recipient  IN VARCHAR2,
        p_status     IN VARCHAR2,
        p_message    IN CLOB DEFAULT NULL,
        o_alert_id   OUT NUMBER
    );

    PROCEDURE sp_get_dashboard_stats(
        o_total_hazards      OUT NUMBER,
        o_potholes           OUT NUMBER,
        o_cracks             OUT NUMBER,
        o_animals            OUT NUMBER,
        o_new_hazards        OUT NUMBER,
        o_acknowledged       OUT NUMBER,
        o_repaired           OUT NUMBER,
        o_online_robots      OUT NUMBER
    );

    PROCEDURE sp_pull_hazard_records(
        p_status        IN VARCHAR2 DEFAULT NULL,
        p_hazard_class  IN VARCHAR2 DEFAULT NULL,
        o_records       OUT SYS_REFCURSOR
    );
END pkg_roadbot;
/

CREATE OR REPLACE PACKAGE BODY pkg_roadbot AS

    FUNCTION fn_deg_to_rad(p_deg IN NUMBER) RETURN NUMBER IS
    BEGIN
        RETURN p_deg * (c_pi / 180.0);
    END fn_deg_to_rad;

    FUNCTION fn_haversine_distance(
        p_lat1 IN NUMBER,
        p_lon1 IN NUMBER,
        p_lat2 IN NUMBER,
        p_lon2 IN NUMBER
    ) RETURN NUMBER IS
        d_lat NUMBER;
        d_lon NUMBER;
        rad_lat1 NUMBER;
        rad_lat2 NUMBER;
        a NUMBER;
        c NUMBER;
    BEGIN
        d_lat := fn_deg_to_rad(p_lat2 - p_lat1);
        d_lon := fn_deg_to_rad(p_lon2 - p_lon1);
        rad_lat1 := fn_deg_to_rad(p_lat1);
        rad_lat2 := fn_deg_to_rad(p_lat2);

        a := POWER(SIN(d_lat / 2.0), 2) +
             COS(rad_lat1) * COS(rad_lat2) * POWER(SIN(d_lon / 2.0), 2);
        
        -- Prevent numerical rounding outside [0, 1]
        IF a > 1.0 THEN
            a := 1.0;
        END IF;

        c := 2.0 * ATAN2(SQRT(a), SQRT(1.0 - a));
        RETURN ROUND(c_earth_radius_m * c, 2);
    END fn_haversine_distance;

    FUNCTION fn_calculate_cluster(
        p_lat          IN NUMBER,
        p_lon          IN NUMBER,
        p_hazard_class IN VARCHAR2,
        p_radius_m     IN NUMBER DEFAULT 15.0
    ) RETURN NUMBER IS
        v_count NUMBER := 1;
        CURSOR c_hazards IS
            SELECT latitude, longitude
            FROM hazards
            WHERE LOWER(hazard_class) = LOWER(p_hazard_class)
              AND created_at >= SYSTIMESTAMP - INTERVAL '1' DAY;
    BEGIN
        FOR h IN c_hazards LOOP
            IF fn_haversine_distance(p_lat, p_lon, h.latitude, h.longitude) <= p_radius_m THEN
                v_count := v_count + 1;
            END IF;
        END LOOP;
        RETURN v_count;
    END fn_calculate_cluster;

    FUNCTION fn_calculate_severity(
        p_hazard_class  IN VARCHAR2,
        p_confidence    IN NUMBER,
        p_cluster_count IN NUMBER DEFAULT 1
    ) RETURN NUMBER IS
        v_base_weight NUMBER;
        v_clustering_multiplier NUMBER;
        v_score NUMBER;
    BEGIN
        CASE LOWER(p_hazard_class)
            WHEN 'pothole' THEN v_base_weight := 80.0;
            WHEN 'crack'   THEN v_base_weight := 60.0;
            WHEN 'animal'  THEN v_base_weight := 90.0;
            ELSE v_base_weight := 50.0;
        END CASE;

        v_clustering_multiplier := LEAST(1.0 + (p_cluster_count - 1) * 0.15, 2.0);
        v_score := v_base_weight * p_confidence * v_clustering_multiplier;

        RETURN ROUND(LEAST(100.0, v_score), 2);
    END fn_calculate_severity;

    PROCEDURE sp_insert_hazard(
        p_robot_id             IN VARCHAR2,
        p_hazard_class         IN VARCHAR2,
        p_confidence           IN NUMBER,
        p_latitude             IN NUMBER,
        p_longitude            IN NUMBER,
        p_bbox_x1              IN NUMBER DEFAULT NULL,
        p_bbox_y1              IN NUMBER DEFAULT NULL,
        p_bbox_x2              IN NUMBER DEFAULT NULL,
        p_bbox_y2              IN NUMBER DEFAULT NULL,
        p_snapshot_path        IN VARCHAR2 DEFAULT NULL,
        p_reported_by          IN VARCHAR2 DEFAULT NULL,
        o_hazard_id            OUT NUMBER,
        o_severity_score       OUT NUMBER,
        o_cluster_count        OUT NUMBER
    ) IS
        v_next_id NUMBER;
    BEGIN
        o_cluster_count := fn_calculate_cluster(p_latitude, p_longitude, p_hazard_class);
        o_severity_score := fn_calculate_severity(p_hazard_class, p_confidence, o_cluster_count);

        SELECT hazard_id_seq.NEXTVAL INTO v_next_id FROM dual;

        INSERT INTO hazards (
            id, robot_id, hazard_class, confidence, latitude, longitude,
            bbox_x1, bbox_y1, bbox_x2, bbox_y2, snapshot_path, severity_score,
            cluster_count, status, reported_by, created_at, updated_at
        ) VALUES (
            v_next_id, p_robot_id, LOWER(p_hazard_class), p_confidence, p_latitude, p_longitude,
            p_bbox_x1, p_bbox_y1, p_bbox_x2, p_bbox_y2, p_snapshot_path, o_severity_score,
            o_cluster_count, 'new', p_reported_by, SYSTIMESTAMP, SYSTIMESTAMP
        );

        o_hazard_id := v_next_id;
    END sp_insert_hazard;

    PROCEDURE sp_update_hazard_status(
        p_hazard_id     IN NUMBER,
        p_new_status    IN VARCHAR2,
        p_user_role     IN VARCHAR2 DEFAULT 'admin',
        o_updated_at    OUT TIMESTAMP
    ) IS
        v_status VARCHAR2(20);
    BEGIN
        v_status := LOWER(p_new_status);

        IF v_status NOT IN ('new', 'acknowledged', 'repaired') THEN
            raise_application_error(-20002, 'Invalid status: ' || p_new_status || '. Must be new, acknowledged, or repaired.');
        END IF;

        IF v_status = 'repaired' AND LOWER(p_user_role) != 'admin' THEN
            raise_application_error(-20001, 'Unauthorized: Only admins can mark hazards as repaired.');
        END IF;

        UPDATE hazards
        SET status = v_status,
            updated_at = SYSTIMESTAMP
        WHERE id = p_hazard_id
        RETURNING updated_at INTO o_updated_at;

        IF SQL%ROWCOUNT = 0 THEN
            raise_application_error(-20003, 'Hazard ID not found: ' || p_hazard_id);
        END IF;
    END sp_update_hazard_status;

    PROCEDURE sp_record_heartbeat(
        p_robot_id           IN VARCHAR2,
        p_status             IN VARCHAR2,
        p_battery_percentage IN NUMBER,
        p_latitude           IN NUMBER DEFAULT NULL,
        p_longitude          IN NUMBER DEFAULT NULL,
        p_speed              IN NUMBER DEFAULT 0.0,
        p_ip_address         IN VARCHAR2 DEFAULT NULL
    ) IS
    BEGIN
        MERGE INTO robot_status target
        USING (SELECT p_robot_id AS robot_id FROM dual) src
        ON (target.robot_id = src.robot_id)
        WHEN MATCHED THEN
            UPDATE SET
                target.status = LOWER(p_status),
                target.battery_percentage = p_battery_percentage,
                target.current_latitude = NVL(p_latitude, target.current_latitude),
                target.current_longitude = NVL(p_longitude, target.current_longitude),
                target.speed = p_speed,
                target.ip_address = NVL(p_ip_address, target.ip_address),
                target.last_seen = SYSTIMESTAMP
        WHEN NOT MATCHED THEN
            INSERT (
                robot_id, status, battery_percentage, current_latitude, current_longitude,
                speed, ip_address, last_seen
            ) VALUES (
                p_robot_id, LOWER(p_status), p_battery_percentage, p_latitude, p_longitude,
                p_speed, p_ip_address, SYSTIMESTAMP
            );
    END sp_record_heartbeat;

    PROCEDURE sp_log_alert(
        p_hazard_id  IN NUMBER,
        p_channel    IN VARCHAR2,
        p_recipient  IN VARCHAR2,
        p_status     IN VARCHAR2,
        p_message    IN CLOB DEFAULT NULL,
        o_alert_id   OUT NUMBER
    ) IS
    BEGIN
        SELECT alert_log_id_seq.NEXTVAL INTO o_alert_id FROM dual;

        INSERT INTO alert_logs (
            id, hazard_id, channel, recipient, status, message, sent_at
        ) VALUES (
            o_alert_id, p_hazard_id, LOWER(p_channel), p_recipient, LOWER(p_status), p_message, SYSTIMESTAMP
        );
    END sp_log_alert;

    PROCEDURE sp_get_dashboard_stats(
        o_total_hazards      OUT NUMBER,
        o_potholes           OUT NUMBER,
        o_cracks             OUT NUMBER,
        o_animals            OUT NUMBER,
        o_new_hazards        OUT NUMBER,
        o_acknowledged       OUT NUMBER,
        o_repaired           OUT NUMBER,
        o_online_robots      OUT NUMBER
    ) IS
    BEGIN
        SELECT COUNT(*) INTO o_total_hazards FROM hazards;
        SELECT NVL(SUM(CASE WHEN LOWER(hazard_class) = 'pothole' THEN 1 ELSE 0 END), 0) INTO o_potholes FROM hazards;
        SELECT NVL(SUM(CASE WHEN LOWER(hazard_class) = 'crack' THEN 1 ELSE 0 END), 0) INTO o_cracks FROM hazards;
        SELECT NVL(SUM(CASE WHEN LOWER(hazard_class) = 'animal' THEN 1 ELSE 0 END), 0) INTO o_animals FROM hazards;
        SELECT NVL(SUM(CASE WHEN LOWER(status) = 'new' THEN 1 ELSE 0 END), 0) INTO o_new_hazards FROM hazards;
        SELECT NVL(SUM(CASE WHEN LOWER(status) = 'acknowledged' THEN 1 ELSE 0 END), 0) INTO o_acknowledged FROM hazards;
        SELECT NVL(SUM(CASE WHEN LOWER(status) = 'repaired' THEN 1 ELSE 0 END), 0) INTO o_repaired FROM hazards;
        
        -- Robots seen within last 60 seconds considered online
        SELECT COUNT(*) INTO o_online_robots
        FROM robot_status
        WHERE last_seen >= SYSTIMESTAMP - INTERVAL '60' SECOND
          AND status != 'offline';
    END sp_get_dashboard_stats;

    PROCEDURE sp_pull_hazard_records(
        p_status        IN VARCHAR2 DEFAULT NULL,
        p_hazard_class  IN VARCHAR2 DEFAULT NULL,
        o_records       OUT SYS_REFCURSOR
    ) IS
    BEGIN
        OPEN o_records FOR
            SELECT id, robot_id, hazard_class, confidence, latitude, longitude,
                   severity_score, cluster_count, status, reported_by, created_at, updated_at
            FROM hazards
            WHERE (p_status IS NULL OR LOWER(status) = LOWER(p_status))
              AND (p_hazard_class IS NULL OR LOWER(hazard_class) = LOWER(p_hazard_class))
            ORDER BY created_at DESC;
    END sp_pull_hazard_records;

END pkg_roadbot;
/

