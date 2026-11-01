# Oracle PL/SQL Database Integration & Migration Guide

This guide details the complete migration of the **Road Hazard Robot Platform** to an enterprise-grade **Oracle PL/SQL Database** (with support for **PostgreSQL PL/pgSQL**).

---

## 1. Overview & Architecture

The platform now supports enterprise relational database engines featuring stored procedures, triggers, sequences, and custom procedural packages:

```mermaid
flowchart TB
    subgraph Edge ["Rover Edge Device"]
        ROBOT["Edge Robot App"] --> BUFFER["Offline SQLite Storage (robot/storage.py)"]
        BUFFER -->|"UART / REST / Plsql Export"| GATEWAY["ESP32 IoT Gateway"]
    end

    subgraph Backend ["FastAPI Cloud Server"]
        GATEWAY --> MQTT["Mosquitto Broker"]
        MQTT --> WORKER["Ingestion Worker"]
        WORKER --> ALCHEMY["SQLAlchemy 2.0 (Thin Driver: oracledb)"]
        FASTAPI["FastAPI REST API"] --> ALCHEMY
    end

    subgraph OracleDB ["Oracle PL/SQL Database (:1521)"]
        ALCHEMY --> TABLES[("Tables: hazards, robot_status, users, alert_logs")]
        TABLES --- TRIGGERS["PL/SQL Triggers (Auto ID, Updated Timestamps)"]
        TABLES --- PKG["PKG_ROADBOT Package (Procedures & Spatial Functions)"]
    end
```

### Key Highlights:
- **Zero-Client Installation**: Uses `oracledb` in Thin Mode—no Oracle Instant Client installation, C compilation, or environment variables needed.
- **Enterprise Procedural Logic**: Core computational tasks (spatial clustering, severity scoring, access control, and telemetry upsert) are encapsulated inside the Oracle PL/SQL package `PKG_ROADBOT`.
- **Dual Support**: Full support for Oracle PL/SQL (`database/oracle_plsql/`) and PostgreSQL PL/pgSQL (`database/postgres_plpgsql/`).

---

## 2. PL/SQL Database Objects

All PL/SQL files reside in `database/oracle_plsql/`:

| File | Description | Key Objects |
| :--- | :--- | :--- |
| `01_schema.sql` | DDL for tables, constraints, indexes & sequences | `hazards`, `robot_status`, `users`, `alert_logs`, `offline_events`, sequences |
| `02_triggers.sql` | Automatic ID and timestamp triggers | `trg_hazards_bi_id`, `trg_hazards_bu_timestamp`, `trg_robot_status_bu_last_seen` |
| `03_package_roadbot.sql` | Stored procedures and spatial math | `PKG_ROADBOT` (Package specification & body) |
| `04_seed_data.sql` | Default users and sample hazards | Default `admin` user, initial telemetry, sample hazards |
| `init_all.sql` | Master script | Executes all scripts sequentially in SQL*Plus or SQLcl |

### `PKG_ROADBOT` Procedures & Functions

- **`fn_haversine_distance(p_lat1, p_lon1, p_lat2, p_lon2)`**: Calculates distance in meters between two GPS coordinates using the Haversine formula in pure PL/SQL.
- **`fn_calculate_cluster(p_lat, p_lon, p_hazard_class, p_radius_m)`**: Queries and counts neighboring hazards of the same type within `p_radius_m` (default: 15m) reported in the last 24 hours.
- **`fn_calculate_severity(p_hazard_class, p_confidence, p_cluster_count)`**: Computes hazard severity according to the Algorithm 1 specification:
  $$\text{Severity} = \min\left(100.0, \text{base\_weight} \times \text{confidence} \times \min\left(1.0 + (\text{cluster} - 1) \times 0.15, 2.0\right)\right)$$
- **`sp_insert_hazard(...)`**: Validates, computes clustering and severity, and inserts hazard, returning the generated `hazard_id` and calculated `severity_score`.
- **`sp_update_hazard_status(p_hazard_id, p_new_status, p_user_role, o_updated_at)`**: Enforces role-based permissions (only admins can mark as `repaired`) and records the update timestamp.
- **`sp_record_heartbeat(...)`**: Performs an atomic `MERGE INTO robot_status` to upsert robot coordinates, battery level, speed, and status.
- **`sp_log_alert(...)`**: Inserts audit trail records into `alert_logs`.
- **`sp_get_dashboard_stats(...)`**: Produces fleet-level KPIs in a single round-trip.

---

## 3. Running with Docker Compose

Spin up Oracle Database 23ai Free:

```bash
# Start Oracle Database container
docker compose up -d oracle

# View initialization logs
docker compose logs -f oracle
```

The container automatically executes all scripts located in `database/oracle_plsql/` upon initial launch.

---

## 4. Connecting the Backend to Oracle PL/SQL

Set your connection string in `.env`:

```env
# Oracle 23ai Free (Docker)
DATABASE_URL=oracle+oracledb://roadbot:roadbot_pass@localhost:1521/?service_name=FREEPDB1

# Or Oracle Express Edition (XE)
# DATABASE_URL=oracle+oracledb://roadbot:roadbot_pass@localhost:1521/XE
```

Launch the FastAPI cloud backend:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

FastAPI automatically initializes the SQLAlchemy connection pool using `oracledb` Thin Mode.

---

## 5. Migrating Data from SQLite / PostgreSQL to PL/SQL

To migrate existing hazards, users, and telemetry from your local SQLite database (`hazards.db`) into your PL/SQL database:

```bash
# Run migration utility
python scripts/migrate_to_plsql.py \
  --source-url sqlite:///./hazards.db \
  --target-url "oracle+oracledb://roadbot:roadbot_pass@localhost:1521/?service_name=FREEPDB1"
```

The migrator will:
1. Recreate tables and sequences in target database if needed.
2. Transfer users, telemetry records, hazards, and alert logs.
3. Automatically synchronize Oracle sequence counters (`hazard_id_seq`, `user_id_seq`, `alert_log_id_seq`) to $\max(\text{id}) + 1$.
4. Validate record count parity across source and target.

---

## 6. Offline Rover Event Synchronization

When the edge rover operates in tunnels or offline environments, it logs detections to `robot/storage.py`. When returning to dock, offline events can be exported as an executable Oracle PL/SQL script:

```python
from robot.storage import LocalStorage

storage = LocalStorage("robot_events.db")
# Export unsynced offline events to PL/SQL script
storage.export_to_plsql_script("offline_sync.sql")
```

The exported script executes `pkg_roadbot.sp_insert_hazard` directly in the database.

