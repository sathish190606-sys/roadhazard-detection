-- ============================================================================
-- Road Hazard Robot Fleet Operations - Oracle PL/SQL Master Setup Script
-- File: init_all.sql
-- ============================================================================

PROMPT ============================================================================
PROMPT Initializing Road Hazard Robot Oracle PL/SQL Database...
PROMPT ============================================================================

PROMPT 1. Executing Table and Sequence DDL...
@@01_schema.sql

PROMPT 2. Creating Database Triggers...
@@02_triggers.sql

PROMPT 3. Compiling PKG_ROADBOT Package Specification & Body...
@@03_package_roadbot.sql

PROMPT 4. Populating Seed Data & Initial Robot Telemetry...
@@04_seed_data.sql

PROMPT ============================================================================
PROMPT Oracle PL/SQL Database Initialized Successfully!
PROMPT ============================================================================
COMMIT;
EXIT;

