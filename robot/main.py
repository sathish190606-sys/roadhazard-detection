import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import yaml
import time
import signal
import argparse
import threading

from robot.logger import logger
from robot.motors import MotorController
from robot.ultrasonic import UltrasonicManager
from robot.gps import GPSManager
from robot.camera import CameraManager
from robot.detector import HazardDetector
from robot.storage import LocalStorage
from robot.iot_client import IoTClient
from robot.navigation import Navigator

# HALs
from robot.hal.mock import (
    MockMotorHAL,
    MockUltrasonicHAL,
    MockGPSHAL,
    MockCameraHAL,
    MockSerialHAL
)
from robot.hal.hardware import (
    HardwareMotorHAL,
    HardwareUltrasonicHAL,
    HardwareGPSHAL,
    HardwareCameraHAL,
    HardwareSerialHAL
)

class RobotApplication:
    def __init__(self, config_path: str = "robot/config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self.detection_thread = None

        self._init_system()

    def _load_config(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def _init_system(self):
        mode = self.config.get("robot", {}).get("mode", "simulation").lower()
        logger.info(f"Initializing Road Hazard Robot in [{mode.upper()}] mode...")

        # 1. Initialize HALs
        if mode == "hardware":
            hw = self.config["hardware"]
            motors_hal = HardwareMotorHAL(**hw["motors"])
            ultrasonic_hal = HardwareUltrasonicHAL(hw["ultrasonic"])
            gps_hal = HardwareGPSHAL(hw["gps"]["port"], hw["gps"]["baudrate"])
            camera_hal = HardwareCameraHAL()
            serial_hal = HardwareSerialHAL(hw["esp32_uart"]["port"], hw["esp32_uart"]["baudrate"])
        else:
            waypoints = self.config.get("navigation", {}).get("waypoints", [])
            motors_hal = MockMotorHAL()
            ultrasonic_hal = MockUltrasonicHAL(simulate_obstacles=True)
            gps_hal = MockGPSHAL(waypoints)
            camera_hal = MockCameraHAL()
            serial_hal = MockSerialHAL()

        # 2. Managers
        nav_cfg = self.config.get("navigation", {})
        det_cfg = self.config.get("detector", {})

        self.motors = MotorController(motors_hal, default_speed_pwm=nav_cfg.get("patrol_speed_pwm", 70))
        self.ultrasonic = UltrasonicManager(ultrasonic_hal)
        self.gps = GPSManager(gps_hal)
        self.camera = CameraManager(camera_hal)

        self.detector = HazardDetector(
            model_path=det_cfg.get("model_path", "ml/weights/yolov8n.pt"),
            confidence_threshold=det_cfg.get("confidence_threshold", 0.5),
            save_snapshot=det_cfg.get("save_cropped_snapshot", True),
            dedup_distance_m=det_cfg.get("dedup", {}).get("distance_threshold_m", 5.0),
            dedup_time_sec=det_cfg.get("dedup", {}).get("time_window_sec", 10.0),
        )

        db_path = self.config.get("storage", {}).get("db_path", "robot_events.db")
        self.storage = LocalStorage(db_path)

        uart_cfg = self.config.get("hardware", {}).get("esp32_uart", {})
        self.iot_client = IoTClient(
            serial_hal=serial_hal,
            storage=self.storage,
            ack_timeout_sec=uart_cfg.get("ack_timeout_sec", 2.0),
            max_retries=uart_cfg.get("max_retries", 3)
        )

        self.navigator = Navigator(
            motors=self.motors,
            ultrasonic=self.ultrasonic,
            gps=self.gps,
            waypoints=nav_cfg.get("waypoints", []),
            min_obstacle_dist_cm=nav_cfg.get("min_obstacle_distance_cm", 30.0),
            backup_duration_sec=nav_cfg.get("backup_duration_sec", 0.6),
            turn_duration_sec=nav_cfg.get("turn_duration_sec", 1.0),
            patrol_speed_pwm=nav_cfg.get("patrol_speed_pwm", 70),
            avoidance_speed_pwm=nav_cfg.get("avoidance_speed_pwm", 50),
            watchdog_timeout_sec=nav_cfg.get("watchdog_timeout_sec", 0.5)
        )

    def start(self, max_seconds: int = 0):
        self.running = True
        logger.info("System initialized successfully. Starting patrol and detection threads...")

        # Start navigation thread
        self.navigator.start_patrol()

        # Start decoupled YOLO detection thread
        self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.detection_thread.start()

        start_time = time.time()
        try:
            while self.running:
                time.sleep(1.0)
                # Periodic offline queue resync
                self.iot_client.sync_offline_queue()

                if max_seconds > 0 and (time.time() - start_time) >= max_seconds:
                    logger.info(f"Target duration {max_seconds}s reached. Shutting down robot.")
                    break
        except KeyboardInterrupt:
            logger.info("Shutdown signal received.")
        finally:
            self.stop()

    def _detection_loop(self):
        """Runs in background thread so YOLO inference never blocks ultrasonic obstacle avoidance!"""
        robot_id = self.config.get("robot", {}).get("id", "robot-01")
        logger.info("YOLOv8 Hazard Detection loop started.")

        while self.running:
            try:
                frame = self.camera.capture_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                lat, lon, _ = self.gps.get_coordinates()
                if lat is None or lon is None:
                    lat, lon = 12.9716, 77.5946

                # Run inference + dedup
                hazards = self.detector.detect(frame, lat, lon)
                for h in hazards:
                    h["robot_id"] = robot_id
                    logger.info(f"Hazard identified: {h['hazard_class'].upper()} (conf: {h['confidence']}) at ({lat}, {lon})")
                    # Send via ESP32 UART
                    self.iot_client.send_hazard_event(h)

                # Target ~10 FPS (100ms cycle)
                time.sleep(0.08)
            except Exception as e:
                logger.error(f"Error in detection thread: {e}")
                time.sleep(0.2)

    def stop(self):
        self.running = False
        if hasattr(self, "navigator"):
            self.navigator.stop_patrol()
        if hasattr(self, "camera"):
            self.camera.release()
        logger.info("Robot systems stopped safely.")

def main():
    parser = argparse.ArgumentParser(description="Autonomous Road Hazard Patrol Robot Application")
    parser.add_argument("--config", default="robot/config.yaml", help="Path to config.yaml")
    parser.add_argument("--duration", type=int, default=0, help="Run duration in seconds (0 = infinite)")
    args = parser.parse_args()

    app = RobotApplication(args.config)

    def handle_sig(sig, frame):
        logger.info("Terminating robot application...")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    app.start(max_seconds=args.duration)

if __name__ == "__main__":
    main()
