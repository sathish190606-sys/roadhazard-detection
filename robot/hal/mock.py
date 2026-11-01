import time
import random
import json
from typing import Optional, Tuple, Any
from PIL import Image, ImageDraw

from robot.hal.base import MotorHALBase, UltrasonicHALBase, GPSHALBase, CameraHALBase, SerialHALBase
from robot.logger import logger

class MockMotorHAL(MotorHALBase):
    def __init__(self):
        self.state = "STOPPED"
        self.current_speed = 0

    def forward(self, speed_pwm: int = 70):
        self.state = "FORWARD"
        self.current_speed = speed_pwm
        logger.debug(f"[MOCK MOTOR] Moving FORWARD (PWM: {speed_pwm})")

    def backward(self, speed_pwm: int = 50):
        self.state = "BACKWARD"
        self.current_speed = speed_pwm
        logger.debug(f"[MOCK MOTOR] Moving BACKWARD (PWM: {speed_pwm})")

    def turn_left(self, speed_pwm: int = 50):
        self.state = "TURN_LEFT"
        self.current_speed = speed_pwm
        logger.debug(f"[MOCK MOTOR] Steering LEFT (PWM: {speed_pwm})")

    def turn_right(self, speed_pwm: int = 50):
        self.state = "TURN_RIGHT"
        self.current_speed = speed_pwm
        logger.debug(f"[MOCK MOTOR] Steering RIGHT (PWM: {speed_pwm})")

    def stop(self):
        self.state = "STOPPED"
        self.current_speed = 0
        logger.debug("[MOCK MOTOR] Motors STOPPED")

    def cleanup(self):
        self.stop()

class MockUltrasonicHAL(UltrasonicHALBase):
    def __init__(self, simulate_obstacles: bool = True):
        self.simulate_obstacles = simulate_obstacles
        self.step_count = 0

    def get_distance(self, sensor: str) -> float:
        self.step_count += 1
        # Every 40 steps, simulate an obstacle ahead (< 30 cm) to verify obstacle avoidance maneuver
        if self.simulate_obstacles and (self.step_count % 45 in [15, 16, 17]) and sensor == "front":
            dist = round(random.uniform(15.0, 26.0), 1)
            logger.info(f"[MOCK ULTRASONIC] Simulated obstacle detected! {sensor} = {dist} cm (< 30 cm)")
            return dist

        # Nominal road clearance
        return round(random.uniform(65.0, 120.0), 1)

    def cleanup(self):
        pass

class MockGPSHAL(GPSHALBase):
    def __init__(self, waypoints=None):
        self.waypoints = waypoints or [
            [12.971600, 77.594600],
            [12.971750, 77.595100],
            [12.972150, 77.595750],
            [12.972750, 77.595800],
        ]
        self.idx = 0
        self.speed = 1.2

    def read_fix(self) -> Tuple[Optional[float], Optional[float], float]:
        lat, lon = self.waypoints[self.idx]
        # Slight GPS jitter
        noisy_lat = lat + random.uniform(-0.00001, 0.00001)
        noisy_lon = lon + random.uniform(-0.00001, 0.00001)
        self.idx = (self.idx + 1) % len(self.waypoints)
        return (round(noisy_lat, 6), round(noisy_lon, 6), self.speed)

class MockCameraHAL(CameraHALBase):
    def __init__(self):
        self.classes = ["pothole", "crack", "animal"]
        self.frame_count = 0

    def read_frame(self) -> Any:
        self.frame_count += 1
        # Synthetic road image
        img = Image.new("RGB", (320, 240), color=(40, 42, 45))
        draw = ImageDraw.Draw(img)
        draw.line([(0, 30), (320, 30)], fill=(220, 220, 220), width=3)
        draw.line([(0, 210), (320, 210)], fill=(220, 220, 220), width=3)
        # Periodically synthesize a hazard
        if self.frame_count % 8 == 0:
            h_class = random.choice(self.classes)
            draw.ellipse([120, 90, 200, 150], fill=(15, 15, 18), outline=(255, 69, 58), width=2)
            draw.text((125, 75), h_class.upper(), fill=(255, 69, 58))
        return img

    def release(self):
        pass

class MockSerialHAL(SerialHALBase):
    """Simulates bidirectional UART with the ESP32 module, generating valid ACKs."""
    def __init__(self):
        self.last_seq = None

    def write_line(self, line: str) -> bool:
        logger.debug(f"[MOCK UART TX -> ESP32]: {line.strip()}")
        try:
            data = json.loads(line)
            self.last_seq = data.get("seq", 1)
        except Exception:
            self.last_seq = 1
        return True

    def read_line(self, timeout_sec: float = 1.0) -> Optional[str]:
        # Return ACK matching the last sequence number
        if self.last_seq is not None:
            ack_msg = json.dumps({"ack": self.last_seq, "status": "OK"})
            self.last_seq = None
            return ack_msg
        return None
