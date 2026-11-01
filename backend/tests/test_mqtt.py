import json
import pytest
from backend.app.schemas import HazardCreate, RobotHeartbeat
from backend.app.mqtt_client import mqtt_subscriber

def test_mqtt_hazard_schema_validation():
    valid_payload = {
        "robot_id": "robot-esp32-01",
        "hazard_class": "crack",
        "confidence": 0.76,
        "latitude": 13.0827,
        "longitude": 80.2707,
        "bbox": {"x1": 50.0, "y1": 50.0, "x2": 150.0, "y2": 150.0}
    }
    hazard = HazardCreate(**valid_payload)
    assert hazard.hazard_class == "crack"
    assert hazard.confidence == 0.76

def test_mqtt_heartbeat_schema_validation():
    valid_payload = {
        "robot_id": "robot-esp32-01",
        "status": "patrol",
        "battery_percentage": 94.0,
        "latitude": 13.0827,
        "longitude": 80.2707,
        "speed": 0.8
    }
    hb = RobotHeartbeat(**valid_payload)
    assert hb.status == "patrol"
    assert hb.battery_percentage == 94.0
