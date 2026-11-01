#!/usr/bin/env python3
"""
Database Migration Utility: Migrate from SQLite/PostgreSQL to Oracle PL/SQL or PostgreSQL PL/pgSQL
Usage:
    python scripts/migrate_to_plsql.py --source-url sqlite:///./hazards.db --target-url oracle+oracledb://roadbot:roadbot_pass@localhost:1521/?service_name=FREEPDB1
"""

import os
import sys
import argparse
import logging
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, text, inspect
from sqlalchemy.orm import sessionmaker
from backend.app.database import normalize_database_url
from backend.app.models import Base, Hazard, RobotStatus, User, AlertLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("plsql_migrator")


def sync_oracle_sequence(conn, table_name: str, seq_name: str, id_col: str = "id"):
    """Adjust Oracle sequence to prevent primary key collision after data load."""
    try:
        max_id_res = conn.execute(text(f"SELECT NVL(MAX({id_col}), 0) FROM {table_name}")).scalar()
        if max_id_res and max_id_res > 0:
            logger.info(f"Syncing Oracle sequence '{seq_name}' to MAX({id_col}) = {max_id_res}...")
            # Drop and recreate sequence to next val
            conn.execute(text(f"DROP SEQUENCE {seq_name}"))
            conn.execute(text(f"CREATE SEQUENCE {seq_name} START WITH {max_id_res + 1} INCREMENT BY 1 NOCACHE"))
    except Exception as e:
        logger.warning(f"Could not reset sequence {seq_name} (may not exist yet or managed by trigger): {e}")


def sync_postgres_sequence(conn, table_name: str, id_col: str = "id"):
    """Reset PostgreSQL serial sequence to MAX(id)."""
    try:
        conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{table_name}', '{id_col}'), COALESCE(MAX({id_col}), 1)) FROM {table_name}"))
    except Exception as e:
        logger.warning(f"Could not reset PostgreSQL sequence for {table_name}: {e}")


def migrate_database(source_url: str, target_url: str, drop_existing: bool = False):
    source_url_norm = normalize_database_url(source_url)
    target_url_norm = normalize_database_url(target_url)

    logger.info(f"Connecting to SOURCE: {source_url_norm}")
    src_kwargs = {"connect_args": {"check_same_thread": False}} if source_url_norm.startswith("sqlite") else {}
    src_engine = create_engine(source_url_norm, **src_kwargs)
    SrcSession = sessionmaker(bind=src_engine)

    logger.info(f"Connecting to TARGET (PL/SQL Database): {target_url_norm}")
    tgt_kwargs = {"pool_pre_ping": True}
    tgt_engine = create_engine(target_url_norm, **tgt_kwargs)
    TgtSession = sessionmaker(bind=tgt_engine)

    is_oracle = "oracle" in tgt_engine.dialect.name.lower()
    is_postgres = "postgres" in tgt_engine.dialect.name.lower()

    if drop_existing:
        logger.info("Dropping existing tables in target...")
        Base.metadata.drop_all(bind=tgt_engine)

    logger.info("Ensuring target schema tables and sequences exist...")
    Base.metadata.create_all(bind=tgt_engine)

    with SrcSession() as src_db, TgtSession() as tgt_db:
        # 1. Migrate Users
        users = src_db.query(User).all()
        logger.info(f"Migrating {len(users)} users...")
        for u in users:
            existing = tgt_db.query(User).filter(User.username == u.username).first()
            if not existing:
                tgt_user = User(
                    id=u.id,
                    username=u.username,
                    hashed_password=u.hashed_password,
                    role=u.role,
                    is_active=u.is_active,
                    created_at=u.created_at
                )
                tgt_db.add(tgt_user)
        tgt_db.commit()

        # 2. Migrate Robot Status
        robots = src_db.query(RobotStatus).all()
        logger.info(f"Migrating {len(robots)} robot telemetry records...")
        for r in robots:
            existing = tgt_db.query(RobotStatus).filter(RobotStatus.robot_id == r.robot_id).first()
            if existing:
                existing.status = r.status
                existing.battery_percentage = r.battery_percentage
                existing.current_latitude = r.current_latitude
                existing.current_longitude = r.current_longitude
                existing.speed = r.speed
                existing.ip_address = r.ip_address
                existing.last_seen = r.last_seen
            else:
                tgt_robot = RobotStatus(
                    robot_id=r.robot_id,
                    status=r.status,
                    battery_percentage=r.battery_percentage,
                    current_latitude=r.current_latitude,
                    current_longitude=r.current_longitude,
                    speed=r.speed,
                    ip_address=r.ip_address,
                    last_seen=r.last_seen
                )
                tgt_db.add(tgt_robot)
        tgt_db.commit()

        # 3. Migrate Hazards
        hazards = src_db.query(Hazard).order_by(Hazard.id.asc()).all()
        logger.info(f"Migrating {len(hazards)} road hazard records...")
        for h in hazards:
            existing = tgt_db.query(Hazard).filter(Hazard.id == h.id).first()
            if not existing:
                tgt_h = Hazard(
                    id=h.id,
                    robot_id=h.robot_id,
                    hazard_class=h.hazard_class,
                    confidence=h.confidence,
                    latitude=h.latitude,
                    longitude=h.longitude,
                    bbox_x1=h.bbox_x1,
                    bbox_y1=h.bbox_y1,
                    bbox_x2=h.bbox_x2,
                    bbox_y2=h.bbox_y2,
                    snapshot_path=h.snapshot_path,
                    repair_snapshot_path=h.repair_snapshot_path,
                    severity_score=h.severity_score,
                    cluster_count=h.cluster_count,
                    status=h.status,
                    reported_by=h.reported_by,
                    created_at=h.created_at,
                    updated_at=h.updated_at
                )
                tgt_db.add(tgt_h)
        tgt_db.commit()

        # 4. Migrate Alert Logs
        alerts = src_db.query(AlertLog).order_by(AlertLog.id.asc()).all()
        logger.info(f"Migrating {len(alerts)} alert logs...")
        for a in alerts:
            existing = tgt_db.query(AlertLog).filter(AlertLog.id == a.id).first()
            if not existing:
                tgt_a = AlertLog(
                    id=a.id,
                    hazard_id=a.hazard_id,
                    channel=a.channel,
                    recipient=a.recipient,
                    status=a.status,
                    message=a.message,
                    sent_at=a.sent_at
                )
                tgt_db.add(tgt_a)
        tgt_db.commit()

        # 5. Reset sequence counters if Oracle or PostgreSQL
        with tgt_engine.begin() as conn:
            if is_oracle:
                sync_oracle_sequence(conn, "users", "user_id_seq")
                sync_oracle_sequence(conn, "hazards", "hazard_id_seq")
                sync_oracle_sequence(conn, "alert_logs", "alert_log_id_seq")
            elif is_postgres:
                sync_postgres_sequence(conn, "users")
                sync_postgres_sequence(conn, "hazards")
                sync_postgres_sequence(conn, "alert_logs")

        # 6. Verification
        src_u_cnt = src_db.query(User).count()
        tgt_u_cnt = tgt_db.query(User).count()
        src_h_cnt = src_db.query(Hazard).count()
        tgt_h_cnt = tgt_db.query(Hazard).count()
        src_r_cnt = src_db.query(RobotStatus).count()
        tgt_r_cnt = tgt_db.query(RobotStatus).count()
        src_a_cnt = src_db.query(AlertLog).count()
        tgt_a_cnt = tgt_db.query(AlertLog).count()

        logger.info("==================================================")
        logger.info("MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("==================================================")
        logger.info(f"Users:        Source={src_u_cnt} | Target={tgt_u_cnt}")
        logger.info(f"Robot Status: Source={src_r_cnt} | Target={tgt_r_cnt}")
        logger.info(f"Hazards:      Source={src_h_cnt} | Target={tgt_h_cnt}")
        logger.info(f"Alert Logs:   Source={src_a_cnt} | Target={tgt_a_cnt}")
        logger.info("==================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Road Hazard DB to PL/SQL database (Oracle / PostgreSQL)")
    parser.add_argument("--source-url", default="sqlite:///./hazards.db", help="Source connection URL")
    parser.add_argument("--target-url", required=True, help="Target PL/SQL connection URL")
    parser.add_argument("--drop-existing", action="store_true", help="Drop target tables before migrating")
    args = parser.parse_args()

    migrate_database(args.source_url, args.target_url, args.drop_existing)

