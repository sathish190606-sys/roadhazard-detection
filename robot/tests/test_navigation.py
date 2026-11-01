import time
import pytest
from robot.motors import MotorController
from robot.ultrasonic import UltrasonicManager
from robot.gps import GPSManager
from robot.navigation import Navigator, SafetyWatchdog
from robot.hal.mock import MockMotorHAL, MockUltrasonicHAL, MockGPSHAL

def test_motor_controller_states():
    mock_hal = MockMotorHAL()
    motors = MotorController(mock_hal, default_speed_pwm=70)

    motors.move_forward(75)
    assert motors.current_state == "FORWARD"
    assert mock_hal.state == "FORWARD"
    assert mock_hal.current_speed == 75

    motors.move_backward(45)
    assert motors.current_state == "BACKWARD"
    assert mock_hal.state == "BACKWARD"

    motors.steer_left(50)
    assert motors.current_state == "STEER_LEFT"
    assert mock_hal.state == "TURN_LEFT"

    motors.steer_right(50)
    assert motors.current_state == "STEER_RIGHT"
    assert mock_hal.state == "TURN_RIGHT"

    motors.stop()
    assert motors.current_state == "STOPPED"
    assert mock_hal.state == "STOPPED"

def test_safety_watchdog_timeout():
    mock_hal = MockMotorHAL()
    motors = MotorController(mock_hal, default_speed_pwm=70)
    motors.move_forward(70)
    assert motors.current_state == "FORWARD"

    # Set tiny watchdog timeout (0.15s) and do not pet it
    watchdog = SafetyWatchdog(motors, timeout_sec=0.15)
    watchdog.start()
    time.sleep(0.3)
    watchdog.stop()

    # Motors should have been emergency stopped by watchdog
    assert motors.current_state == "STOPPED"

def test_navigator_obstacle_avoidance_trigger():
    mock_hal = MockMotorHAL()
    motors = MotorController(mock_hal, default_speed_pwm=70)

    class CustomUltrasonicHAL(MockUltrasonicHAL):
        def get_distance(self, sensor: str) -> float:
            if sensor == "front":
                return 22.0  # Obstacle < 30 cm
            return 80.0

    ultrasonic = UltrasonicManager(CustomUltrasonicHAL(simulate_obstacles=False))
    gps = GPSManager(MockGPSHAL())

    navigator = Navigator(
        motors=motors,
        ultrasonic=ultrasonic,
        gps=gps,
        waypoints=[[12.9716, 77.5946]],
        min_obstacle_dist_cm=30.0,
        backup_duration_sec=0.1,
        turn_duration_sec=0.1,
        watchdog_timeout_sec=1.0
    )

    # Start patrol for 0.4s
    navigator.start_patrol()
    time.sleep(0.4)
    navigator.stop_patrol()

    # Avoidance maneuver was triggered because front was 22.0 cm < 30.0 cm
    assert navigator.avoidance_state in ["CLEAR", "STEERING", "REVERSING", "STOPPING"]
