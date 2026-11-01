-- ============================================================================
-- Road Hazard Robot Fleet Operations - Oracle PL/SQL Seed Data
-- File: 04_seed_data.sql
-- ============================================================================

-- 1. Insert Default Administrator (Password: admin123)
MERGE INTO users u
USING (SELECT 'admin' AS username FROM dual) s
ON (u.username = s.username)
WHEN NOT MATCHED THEN
    INSERT (id, username, hashed_password, role, is_active, created_at)
    VALUES (user_id_seq.NEXTVAL, 'admin', '$2b$12$rOrOFF1m08EmXS0aX9SiNe824JoycUFKEgxszbCoQFIDzShSXDPV.', 'admin', 1, SYSTIMESTAMP);

-- 2. Insert Default Viewer User (Password: viewer123)
MERGE INTO users u
USING (SELECT 'viewer' AS username FROM dual) s
ON (u.username = s.username)
WHEN NOT MATCHED THEN
    INSERT (id, username, hashed_password, role, is_active, created_at)
    VALUES (user_id_seq.NEXTVAL, 'viewer', '$2b$12$rOrOFF1m08EmXS0aX9SiNe824JoycUFKEgxszbCoQFIDzShSXDPV.', 'viewer', 1, SYSTIMESTAMP);

-- 3. Initial Active Rover Status
BEGIN
    pkg_roadbot.sp_record_heartbeat(
        p_robot_id           => 'robot-01',
        p_status             => 'patrol',
        p_battery_percentage => 92.5,
        p_latitude           => 12.97185,
        p_longitude          => 77.59472,
        p_speed              => 1.4,
        p_ip_address         => '192.168.1.145'
    );
END;
/

-- 4. Initial Sample Hazards using PL/SQL Package
DECLARE
    v_id1 NUMBER;
    v_score1 NUMBER;
    v_cluster1 NUMBER;

    v_id2 NUMBER;
    v_score2 NUMBER;
    v_cluster2 NUMBER;

    v_id3 NUMBER;
    v_score3 NUMBER;
    v_cluster3 NUMBER;
BEGIN
    -- Pothole Hazard
    pkg_roadbot.sp_insert_hazard(
        p_robot_id       => 'robot-01',
        p_hazard_class   => 'pothole',
        p_confidence     => 0.94,
        p_latitude       => 12.97165,
        p_longitude      => 77.59462,
        p_bbox_x1        => 120.0,
        p_bbox_y1        => 200.0,
        p_bbox_x2        => 310.0,
        p_bbox_y2        => 380.0,
        p_snapshot_path  => 'uploads/pothole_demo_01.jpg',
        p_reported_by    => NULL,
        o_hazard_id      => v_id1,
        o_severity_score => v_score1,
        o_cluster_count  => v_cluster1
    );

    -- Surface Crack Hazard
    pkg_roadbot.sp_insert_hazard(
        p_robot_id       => 'robot-01',
        p_hazard_class   => 'crack',
        p_confidence     => 0.88,
        p_latitude       => 12.97210,
        p_longitude      => 77.59510,
        p_bbox_x1        => 80.0,
        p_bbox_y1        => 150.0,
        p_bbox_x2        => 250.0,
        p_bbox_y2        => 320.0,
        p_snapshot_path  => 'uploads/crack_demo_02.jpg',
        p_reported_by    => NULL,
        o_hazard_id      => v_id2,
        o_severity_score => v_score2,
        o_cluster_count  => v_cluster2
    );

    -- Stray Animal Obstacle
    pkg_roadbot.sp_insert_hazard(
        p_robot_id       => 'robot-01',
        p_hazard_class   => 'animal',
        p_confidence     => 0.91,
        p_latitude       => 12.97280,
        p_longitude      => 77.59580,
        p_bbox_x1        => 140.0,
        p_bbox_y1        => 180.0,
        p_bbox_x2        => 360.0,
        p_bbox_y2        => 420.0,
        p_snapshot_path  => 'uploads/animal_demo_03.jpg',
        p_reported_by    => NULL,
        o_hazard_id      => v_id3,
        o_severity_score => v_score3,
        o_cluster_count  => v_cluster3
    );

    COMMIT;
END;
/

