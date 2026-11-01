from robot.hal.base import MotorHALBase
from robot.logger import logger

class MotorController:
    def __init__(self, hal: MotorHALBase, default_speed_pwm: int = 70):
        self.hal = hal
        self.default_speed = default_speed_pwm
        self.current_state = "STOPPED"

    def move_forward(self, speed_pwm: int = None):
        spd = speed_pwm or self.default_speed
        self.current_state = "FORWARD"
        self.hal.forward(spd)

    def move_backward(self, speed_pwm: int = None):
        spd = speed_pwm or int(self.default_speed * 0.7)
        self.current_state = "BACKWARD"
        self.hal.backward(spd)

    def steer_left(self, speed_pwm: int = None):
        spd = speed_pwm or int(self.default_speed * 0.7)
        self.current_state = "STEER_LEFT"
        self.hal.turn_left(spd)

    def steer_right(self, speed_pwm: int = None):
        spd = speed_pwm or int(self.default_speed * 0.7)
        self.current_state = "STEER_RIGHT"
        self.hal.turn_right(spd)

    def stop(self):
        self.current_state = "STOPPED"
        self.hal.stop()

    def emergency_stop(self):
        logger.warning("EMERGENCY STOP TRIGGERED!")
        self.stop()
