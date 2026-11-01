import os
import pytest
from sqlalchemy.schema import CreateTable, CreateSequence
from sqlalchemy.dialects import oracle

from backend.app.database import normalize_database_url
from backend.app.models import Base, Hazard, RobotStatus, User, AlertLog
from robot.storage import LocalStorage

def test_normalize_database_url():
    url_oracle = "oracle://roadbot:pass@localhost:1521/XE"
    assert normalize_database_url(url_oracle) == "oracle+oracledb://roadbot:pass@localhost:1521/XE"

    url_oracle_thin = "oracle+oracledb://roadbot:pass@localhost:1521/?service_name=FREEPDB1"
    assert normalize_database_url(url_oracle_thin) == url_oracle_thin

    url_pg = "postgres://roadbot:pass@localhost:5432/db"
    assert normalize_database_url(url_pg) == "postgresql+psycopg2://roadbot:pass@localhost:5432/db"

    url_sqlite = "sqlite:///./hazards.db"
    assert normalize_database_url(url_sqlite) == url_sqlite

def test_oracle_ddl_compilation():
    """Verify that all SQLAlchemy models and sequences compile cleanly into Oracle DDL."""
    dialect = oracle.dialect()

    for name, table in Base.metadata.tables.items():
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert "CREATE TABLE" in ddl
        assert name in ddl

    # Verify sequences compile
    for seq in [Hazard.__table__.columns["id"].default, User.__table__.columns["id"].default]:
        if seq and hasattr(seq, "name"):
            seq_ddl = str(CreateSequence(seq).compile(dialect=dialect))
            assert "CREATE SEQUENCE" in seq_ddl

def test_oracle_plsql_files_exist_and_valid():
    """Verify that all Oracle PL/SQL scripts are in place and non-empty."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    plsql_dir = os.path.join(base_dir, "database", "oracle_plsql")
    
    expected_files = [
        "01_schema.sql",
        "02_triggers.sql",
        "03_package_roadbot.sql",
        "04_seed_data.sql",
        "init_all.sql"
    ]

    for fname in expected_files:
        fpath = os.path.join(plsql_dir, fname)
        assert os.path.isfile(fpath), f"Missing {fpath}"
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 50, f"File {fname} is too small"

    # Verify key PL/SQL symbols in package
    with open(os.path.join(plsql_dir, "03_package_roadbot.sql"), "r", encoding="utf-8") as f:
        pkg = f.read()
        assert "CREATE OR REPLACE PACKAGE pkg_roadbot" in pkg
        assert "sp_insert_hazard" in pkg
        assert "sp_update_hazard_status" in pkg
        assert "fn_haversine_distance" in pkg
        assert "fn_calculate_severity" in pkg

def test_robot_storage_export_to_plsql(tmp_path):
    """Verify that edge LocalStorage correctly formats offline events for PL/SQL ingestion."""
    db_file = str(tmp_path / "test_robot.db")
    storage = LocalStorage(db_path=db_file)
    
    storage.save_event(101, {
        "robot_id": "robot-01",
        "hazard_class": "pothole",
        "confidence": 0.95,
        "latitude": 12.9716,
        "longitude": 77.5946
    })

    script = storage.export_to_plsql_script()
    assert "pkg_roadbot.sp_insert_hazard" in script
    assert "pothole" in script
    assert "12.9716" in script
    assert "COMMIT;" in script

