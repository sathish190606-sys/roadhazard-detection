-- ============================================================================
-- Road Hazard Robot Fleet Operations - Pull Records PL/SQL Script
-- File: 05_pull_records.sql
-- ============================================================================

SET SERVEROUTPUT ON SIZE UNLIMITED;
SET LINESIZE 200;
SET PAGESIZE 1000;

DECLARE
    v_cursor SYS_REFCURSOR;
    
    TYPE t_record IS RECORD (
        id              NUMBER,
        robot_id        VARCHAR2(50),
        hazard_class    VARCHAR2(20),
        confidence      NUMBER,
        latitude        NUMBER,
        longitude       NUMBER,
        severity_score  NUMBER,
        cluster_count   NUMBER,
        status          VARCHAR2(20),
        reported_by     VARCHAR2(50),
        created_at      TIMESTAMP,
        updated_at      TIMESTAMP
    );
    
    rec t_record;
    v_count NUMBER := 0;
BEGIN
    DBMS_OUTPUT.PUT_LINE('========================================================================================================================');
    DBMS_OUTPUT.PUT_LINE('PULLING ROAD HAZARD INSPECTION RECORDS FROM ORACLE PL/SQL DATABASE');
    DBMS_OUTPUT.PUT_LINE('========================================================================================================================');
    DBMS_OUTPUT.PUT_LINE(
        RPAD('ID', 6) ||
        RPAD('CLASS', 12) ||
        RPAD('STATUS', 15) ||
        RPAD('SEVERITY', 12) ||
        RPAD('CONF.', 10) ||
        RPAD('LATITUDE', 14) ||
        RPAD('LONGITUDE', 14) ||
        RPAD('REPORTER', 18) ||
        'TIMESTAMP'
    );
    DBMS_OUTPUT.PUT_LINE('------------------------------------------------------------------------------------------------------------------------');

    -- Invoke PL/SQL package procedure to pull cursor
    pkg_roadbot.sp_pull_hazard_records(
        p_status       => NULL,
        p_hazard_class => NULL,
        o_records      => v_cursor
    );

    LOOP
        FETCH v_cursor INTO rec;
        EXIT WHEN v_cursor%NOTFOUND;
        v_count := v_count + 1;

        DBMS_OUTPUT.PUT_LINE(
            RPAD(TO_CHAR(rec.id), 6) ||
            RPAD(UPPER(rec.hazard_class), 12) ||
            RPAD(rec.status, 15) ||
            RPAD(TO_CHAR(rec.severity_score, '990.00'), 12) ||
            RPAD(TO_CHAR(ROUND(rec.confidence * 100, 1), '990.0') || '%', 10) ||
            RPAD(TO_CHAR(rec.latitude, '990.99999'), 14) ||
            RPAD(TO_CHAR(rec.longitude, '990.99999'), 14) ||
            RPAD(NVL(rec.reported_by, rec.robot_id), 18) ||
            TO_CHAR(rec.created_at, 'YYYY-MM-DD HH24:MI:SS')
        );
    END LOOP;

    CLOSE v_cursor;

    DBMS_OUTPUT.PUT_LINE('========================================================================================================================');
    DBMS_OUTPUT.PUT_LINE('TOTAL RECORDS PULLED: ' || v_count);
    DBMS_OUTPUT.PUT_LINE('========================================================================================================================');
END;
/

