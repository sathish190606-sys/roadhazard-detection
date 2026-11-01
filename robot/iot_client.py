import json
import time
import threading
from typing import Dict, Any, Optional
from robot.hal.base import SerialHALBase
from robot.storage import LocalStorage
from robot.logger import logger

class IoTClient:
    def __init__(
        self,
        serial_hal: SerialHALBase,
        storage: LocalStorage,
        ack_timeout_sec: float = 2.0,
        max_retries: int = 3
    ):
        self.serial_hal = serial_hal
        self.storage = storage
        self.ack_timeout = ack_timeout_sec
        self.max_retries = max_retries
        self.seq_num = 1
        self.lock = threading.Lock()
        self.is_connected = True

    def _next_seq(self) -> int:
        s = self.seq_num
        self.seq_num += 1
        return s

    def send_hazard_event(self, hazard_data: Dict[str, Any]) -> bool:
        """Transmits hazard payload over UART to ESP32 with ACK confirmation and retry."""
        with self.lock:
            seq = self._next_seq()
            frame = {
                "seq": seq,
                "cmd": "HAZARD",
                "data": hazard_data
            }
            json_line = json.dumps(frame)

            for attempt in range(1, self.max_retries + 1):
                logger.info(f"[UART TX] Sending hazard (seq: {seq}, attempt: {attempt}/{self.max_retries})")
                success = self.serial_hal.write_line(json_line)
                if not success:
                    time.sleep(0.3)
                    continue

                # Wait for ACK
                ack_response = self.serial_hal.read_line(timeout_sec=self.ack_timeout)
                if ack_response:
                    try:
                        ack_data = json.loads(ack_response)
                        if ack_data.get("ack") == seq and ack_data.get("status") == "OK":
                            logger.info(f"[UART RX] Received ACK for seq {seq} from ESP32 gateway.")
                            self.is_connected = True
                            return True
                    except Exception:
                        pass

                logger.warning(f"[UART TIMEOUT] No ACK received for seq {seq} on attempt {attempt}.")
                time.sleep(0.5)

            # All retries failed, store offline
            logger.warning(f"ESP32 link unreachable. Buffering seq {seq} in local offline store.")
            self.storage.save_event(seq, hazard_data)
            self.is_connected = False
            return False

    def sync_offline_queue(self):
        """Flushes unacknowledged events from SQLite when connection is healthy."""
        unsent = self.storage.get_unsent_events(limit=10)
        if not unsent:
            return

        logger.info(f"Attempting to re-sync {len(unsent)} offline buffered events...")
        for item in unsent:
            row_id = item["id"]
            payload = item["payload"]
            success = self.send_hazard_event(payload)
            if success:
                self.storage.mark_synced(row_id)
            else:
                break
