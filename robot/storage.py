import sqlite3
import json
import time
from typing import List, Dict, Any, Optional
from robot.logger import logger

class LocalStorage:
    def __init__(self, db_path: str = "robot_events.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seq INTEGER,
                    payload_json TEXT NOT NULL,
                    synced INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_event(self, seq: int, payload: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO offline_events (seq, payload_json, synced) VALUES (?, ?, 0)",
                (seq, json.dumps(payload))
            )
            conn.commit()
            logger.debug(f"Saved event seq {seq} to offline database.")

    def get_unsent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, seq, payload_json FROM offline_events WHERE synced = 0 ORDER BY id ASC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            results = []
            for row_id, seq, p_json in rows:
                results.append({
                    "id": row_id,
                    "seq": seq,
                    "payload": json.loads(p_json)
                })
            return results

    def mark_synced(self, row_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE offline_events SET synced = 1 WHERE id = ?", (row_id,))
            conn.commit()

    def export_to_plsql_script(self, output_path: Optional[str] = None) -> str:
        """Export all unsynced offline events as an executable Oracle PL/SQL script."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, seq, payload_json, created_at FROM offline_events WHERE synced = 0 ORDER BY id ASC")
            rows = cursor.fetchall()

        lines = [
            "-- ============================================================================",
            "-- Road Hazard Robot: Exported Offline Events for Oracle PL/SQL Database Ingestion",
            "-- ============================================================================",
            "SET SERVEROUTPUT ON;",
            "DECLARE",
            "    v_hid NUMBER;",
            "    v_score NUMBER;",
            "    v_cluster NUMBER;",
            "BEGIN"
        ]

        for row_id, seq, p_json, dt in rows:
            try:
                data = json.loads(p_json)
                r_id = data.get("robot_id", "robot-01")
                h_class = data.get("hazard_class", "pothole")
                conf = float(data.get("confidence", 0.8))
                lat = float(data.get("latitude", 0.0))
                lon = float(data.get("longitude", 0.0))
                lines.append(f"    -- Event ID {row_id} (Seq {seq})")
                lines.append(f"    pkg_roadbot.sp_insert_hazard(")
                lines.append(f"        p_robot_id       => '{r_id}',")
                lines.append(f"        p_hazard_class   => '{h_class}',")
                lines.append(f"        p_confidence     => {conf},")
                lines.append(f"        p_latitude       => {lat},")
                lines.append(f"        p_longitude      => {lon},")
                lines.append(f"        o_hazard_id      => v_hid,")
                lines.append(f"        o_severity_score => v_score,")
                lines.append(f"        o_cluster_count  => v_cluster")
                lines.append(f"    );")
            except Exception as e:
                logger.warning(f"Skipping event #{row_id} due to parse error: {e}")

        lines.append("    COMMIT;")
        lines.append("    DBMS_OUTPUT.PUT_LINE('Offline events synchronized successfully.');")
        lines.append("END;")
        lines.append("/")

        script = "\n".join(lines)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(script)
        return script
