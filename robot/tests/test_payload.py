import json
import pytest
from robot.iot_client import IoTClient
from robot.storage import LocalStorage
from robot.hal.mock import MockSerialHAL

def test_iot_client_send_and_ack(tmp_path):
    db_file = str(tmp_path / "test_events.db")
    storage = LocalStorage(db_file)
    mock_serial = MockSerialHAL()

    client = IoTClient(mock_serial, storage, ack_timeout_sec=1.0, max_retries=2)

    hazard_payload = {
        "robot_id": "robot-01",
        "hazard_class": "pothole",
        "confidence": 0.88,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "bbox": {"x1": 50.0, "y1": 50.0, "x2": 150.0, "y2": 150.0}
    }

    # Should succeed with mock ACK
    success = client.send_hazard_event(hazard_payload)
    assert success is True

def test_iot_client_offline_fallback(tmp_path):
    db_file = str(tmp_path / "test_events.db")
    storage = LocalStorage(db_file)

    class FailingSerial(MockSerialHAL):
        def read_line(self, timeout_sec: float = 1.0):
            return None  # Never sends ACK

    failing_serial = FailingSerial()
    client = IoTClient(failing_serial, storage, ack_timeout_sec=0.1, max_retries=1)

    hazard_payload = {
        "robot_id": "robot-01",
        "hazard_class": "crack",
        "confidence": 0.75,
        "latitude": 12.9716,
        "longitude": 77.5946
    }

    success = client.send_hazard_event(hazard_payload)
    assert success is False

    # Should have buffered in SQLite offline storage
    unsent = storage.get_unsent_events()
    assert len(unsent) == 1
    assert unsent[0]["payload"]["hazard_class"] == "crack"
