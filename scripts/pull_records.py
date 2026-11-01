#!/usr/bin/env python3
"""
Pull Road Hazard Inspection Records from Database (Oracle PL/SQL, PostgreSQL, or SQLite)
Usage:
    python scripts/pull_records.py
    python scripts/pull_records.py --status repaired
    python scripts/pull_records.py --export-csv reports/hazards_export.csv
"""

import os
import sys
import argparse
import csv
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from backend.app.config import settings
from backend.app.database import normalize_database_url


def pull_records_from_db(
    db_url: Optional[str] = None,
    status_filter: Optional[str] = None,
    class_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Pull hazard records using PL/SQL procedure if Oracle, or SQL query."""
    url = normalize_database_url(db_url or settings.DATABASE_URL)
    is_oracle = "oracle" in url.lower()
    is_sqlite = url.startswith("sqlite")

    engine_kwargs = {}
    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **engine_kwargs)
    records = []

    if is_oracle:
        import oracledb
        with engine.raw_connection() as raw_conn:
            cursor = raw_conn.cursor()
            try:
                # Use PL/SQL package procedure with SYS_REFCURSOR
                ref_cursor = cursor.var(oracledb.CURSOR)
                cursor.callproc(
                    "pkg_roadbot.sp_pull_hazard_records",
                    [status_filter, class_filter, ref_cursor]
                )
                cur_val = ref_cursor.getvalue()
                col_names = [col[0].lower() for col in cur_val.description]
                for row in cur_val.fetchall():
                    records.append(dict(zip(col_names, row)))
            finally:
                cursor.close()
    else:
        # Standard SQL query
        query_sql = "SELECT id, robot_id, hazard_class, confidence, latitude, longitude, severity_score, cluster_count, status, reported_by, created_at, updated_at FROM hazards WHERE 1=1"
        params = {}
        if status_filter:
            query_sql += " AND LOWER(status) = :status"
            params["status"] = status_filter.lower()
        if class_filter:
            query_sql += " AND LOWER(hazard_class) = :hclass"
            params["hclass"] = class_filter.lower()
        query_sql += " ORDER BY id DESC"

        with engine.connect() as conn:
            result = conn.execute(text(query_sql), params)
            for row in result.mappings():
                records.append(dict(row))

    return records


def format_table(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "No hazard records found."

    headers = ["ID", "CLASS", "STATUS", "SEVERITY", "CONF.", "LATITUDE", "LONGITUDE", "REPORTED BY", "TIMESTAMP"]
    col_widths = [6, 12, 14, 10, 8, 14, 14, 18, 20]

    header_line = "".join(h.ljust(w) for h, w in zip(headers, col_widths))
    sep_line = "-" * len(header_line)

    rows = []
    for r in records:
        dt = r.get("created_at")
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S") if isinstance(dt, datetime) else str(dt)[:19]
        conf = f"{float(r.get('confidence', 0.0)) * 100:.1f}%"
        sev = f"{float(r.get('severity_score', 0.0)):.2f}"
        reporter = str(r.get("reported_by") or r.get("robot_id") or "robot-01")

        row_str = (
            str(r.get("id")).ljust(col_widths[0]) +
            str(r.get("hazard_class", "")).upper().ljust(col_widths[1]) +
            str(r.get("status", "")).ljust(col_widths[2]) +
            sev.ljust(col_widths[3]) +
            conf.ljust(col_widths[4]) +
            f"{float(r.get('latitude', 0.0)):.5f}".ljust(col_widths[5]) +
            f"{float(r.get('longitude', 0.0)):.5f}".ljust(col_widths[6]) +
            reporter.ljust(col_widths[7]) +
            dt_str.ljust(col_widths[8])
        )
        rows.append(row_str)

    return f"{sep_line}\n{header_line}\n{sep_line}\n" + "\n".join(rows) + f"\n{sep_line}"


def export_csv(records: List[Dict[str, Any]], filepath: str):
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    if not records:
        print(f"No records to export to {filepath}")
        return

    fieldnames = list(records[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)
    print(f"Exported {len(records)} records to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Pull Road Hazard Records")
    parser.add_argument("--db-url", default=None, help="Database connection URL")
    parser.add_argument("--status", default=None, help="Filter by status (new, acknowledged, repaired)")
    parser.add_argument("--class", dest="hazard_class", default=None, help="Filter by class (pothole, crack, animal)")
    parser.add_argument("--export-csv", default=None, help="Export records to CSV file path")
    parser.add_argument("--export-json", default=None, help="Export records to JSON file path")
    args = parser.parse_args()

    print("\n" + "=" * 110)
    print("ROAD HAZARD INSPECTION LEDGER - PULLING RECORDS")
    print("=" * 110)

    try:
        records = pull_records_from_db(
            db_url=args.db_url,
            status_filter=args.status,
            class_filter=args.hazard_class
        )
        print(f"Successfully pulled {len(records)} record(s):\n")
        print(format_table(records))

        if args.export_csv:
            export_csv(records, args.export_csv)

        if args.export_json:
            os.makedirs(os.path.dirname(os.path.abspath(args.export_json)), exist_ok=True)
            with open(args.export_json, "w", encoding="utf-8") as f:
                json.dump(records, f, default=str, indent=2)
            print(f"Exported {len(records)} records to {args.export_json}")

    except Exception as e:
        print(f"Error pulling records: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

