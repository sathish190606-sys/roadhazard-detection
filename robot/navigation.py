import time
import math
import threading
from typing import List, Tuple
from robot.motors import MotorController
from robot.ultrasonic import UltrasonicManager
from robot.gps import GPSManager
from robot.logger import logger

class SafetyWatchdog:
    """Monitors navigation loop heartbeat. If thread hangs > timeout, immediately stops motors."""
    def __init__(self, motors: MotorController, timeout_sec: float = 0.5):
        self.motors = motors
        self.timeout = timeout_sec
        self.last_heartbeat = time.time()
        self.running = False
        self.thread = None

    def pet(self):
        self.last_heartbeat = time.time()

    def start(self):
        self.running = True
        self.last_heartbeat = time.time()
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _monitor_loop(self):
        while self.running:
            time.sleep(0.1)
            elapsed = time.time() - self.last_heartbeat
            if elapsed > self.timeout:
                logger.critical(f"WATCHDOG EXPIRED! No heartbeat for {elapsed:.2f}s (> {self.timeout}s). Stopping motors.")
                self.motors.emergency_stop()

class Navigator:
    def __init__(
        self,
        motors: MotorController,
        ultrasonic: UltrasonicManager,
        gps: GPSManager,
        waypoints: List[Tuple[float, float]],
        min_obstacle_dist_cm: float = 30.0,
        backup_duration_sec: float = 0.6,
        turn_duration_sec: float = 1.0,
        patrol_speed_pwm: int = 70,
        avoidance_speed_pwm: int = 50,
        watchdog_timeout_sec: float = 0.5
    ):
        self.motors = motors
        self.ultrasonic = ultrasonic
        self.gps = gps
        self.waypoints = waypoints
        self.min_obstacle_dist = min_obstacle_dist_cm
        self.backup_duration = backup_duration_sec
        self.turn_duration = turn_duration_sec
        self.patrol_speed = patrol_speed_pwm
        self.avoidance_speed = avoidance_speed_pwm

        self.watchdog = SafetyWatchdog(motors, timeout_sec=watchdog_timeout_sec)
        self.is_patrolling = False
        self.nav_thread = None
        self.current_waypoint_idx = 0
        self.avoidance_state = "CLEAR"  # CLEAR, STOPPING, REVERSING, STEERING

    def start_patrol(self):
        logger.info("Starting autonomous patrol loop (Algorithm 1)...")
        self.is_patrolling = True
        self.watchdog.start()
        self.nav_thread = threading.Thread(target=self._patrol_loop, daemon=True)
        self.nav_thread.start()

    def stop_patrol(self):
        logger.info("Stopping autonomous patrol...")
        self.is_patrolling = False
        self.watchdog.stop()
        self.motors.stop()

    def _patrol_loop(self):
        """Executes Algorithm 1 continuously while patrol active."""
        while self.is_patrolling:
            # 1. Pet watchdog
            self.watchdog.pet()

            # 2. Read ultrasonic sensor distances
            distances = self.ultrasonic.read_all_distances()
            f_dist = distances["front"]
            l_dist = distances["left"]
            r_dist = distances["right"]
            min_dist = min(f_dist, l_dist, r_dist)

            # Algorithm 1: Step 2a. If any distance < 30 cm: stop, back up briefly, steer around, resume.
            if min_dist < self.min_obstacle_dist:
                logger.warning(
                    f"Obstacle in path! (Front: {f_dist}cm, Left: {l_dist}cm, Right: {r_dist}cm). "
                    f"Initiating avoidance maneuver..."
                )
                self.avoidance_state = "STOPPING"
                self.motors.stop()
                time.sleep(0.2)

                # Back up briefly
                self.avoidance_state = "REVERSING"
                self.motors.move_backward(self.avoidance_speed)
                time.sleep(self.backup_duration)
                self.watchdog.pet()

                # Steer towards clearer side
                self.avoidance_state = "STEERING"
                if l_dist > r_dist:
                    logger.info("Steering LEFT around obstacle...")
                    self.motors.steer_left(self.avoidance_speed)
                else:
                    logger.info("Steering RIGHT around obstacle...")
                    self.motors.steer_right(self.avoidance_speed)

                time.sleep(self.turn_duration)
                self.watchdog.pet()

                self.motors.stop()
                time.sleep(0.1)
                self.avoidance_state = "CLEAR"
                logger.info("Avoidance maneuver completed. Resuming forward patrol.")
            else:
                # Algorithm 1: Step 2b. Move forward along patrol path
                self.avoidance_state = "CLEAR"
                self.motors.move_forward(self.patrol_speed)

            time.sleep(0.05)  # 20 Hz loop rate
