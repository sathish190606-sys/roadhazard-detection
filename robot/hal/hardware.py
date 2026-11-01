import time
import serial
from typing import Optional, Tuple, Any

from robot.hal.base import MotorHALBase, UltrasonicHALBase, GPSHALBase, CameraHALBase, SerialHALBase
from robot.logger import logger

# Gracefully import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

# Gracefully import OpenCV
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

class HardwareMotorHAL(MotorHALBase):
    def __init__(self, in1=17, in2=27, ena=12, in3=22, in4=23, enb=13):
        self.in1 = in1
        self.in2 = in2
        self.ena = ena
        self.in3 = in3
        self.in4 = in4
        self.enb = enb
        self.pwm_a = None
        self.pwm_b = None

        if not GPIO_AVAILABLE:
            raise RuntimeError("RPi.GPIO is not available on this platform. Use mode: simulation.")

        GPIO.setmode(GPIO.BCM)
        for pin in [in1, in2, ena, in3, in4, enb]:
            GPIO.setup(pin, GPIO.OUT)

        self.pwm_a = GPIO.PWM(ena, 1000)  # 1kHz PWM
        self.pwm_b = GPIO.PWM(enb, 1000)
        self.pwm_a.start(0)
        self.pwm_b.start(0)

    def forward(self, speed_pwm: int = 70):
        # Left forward
        GPIO.output(self.in1, GPIO.HIGH)
        GPIO.output(self.in2, GPIO.LOW)
        # Right forward
        GPIO.output(self.in3, GPIO.HIGH)
        GPIO.output(self.in4, GPIO.LOW)
        self.pwm_a.ChangeDutyCycle(speed_pwm)
        self.pwm_b.ChangeDutyCycle(speed_pwm)

    def backward(self, speed_pwm: int = 50):
        # Left reverse
        GPIO.output(self.in1, GPIO.LOW)
        GPIO.output(self.in2, GPIO.HIGH)
        # Right reverse
        GPIO.output(self.in3, GPIO.LOW)
        GPIO.output(self.in4, GPIO.HIGH)
        self.pwm_a.ChangeDutyCycle(speed_pwm)
        self.pwm_b.ChangeDutyCycle(speed_pwm)

    def turn_left(self, speed_pwm: int = 50):
        # Left reverse, Right forward
        GPIO.output(self.in1, GPIO.LOW)
        GPIO.output(self.in2, GPIO.HIGH)
        GPIO.output(self.in3, GPIO.HIGH)
        GPIO.output(self.in4, GPIO.LOW)
        self.pwm_a.ChangeDutyCycle(speed_pwm)
        self.pwm_b.ChangeDutyCycle(speed_pwm)

    def turn_right(self, speed_pwm: int = 50):
        # Left forward, Right reverse
        GPIO.output(self.in1, GPIO.HIGH)
        GPIO.output(self.in2, GPIO.LOW)
        GPIO.output(self.in3, GPIO.LOW)
        GPIO.output(self.in4, GPIO.HIGH)
        self.pwm_a.ChangeDutyCycle(speed_pwm)
        self.pwm_b.ChangeDutyCycle(speed_pwm)

    def stop(self):
        for pin in [self.in1, self.in2, self.in3, self.in4]:
            GPIO.output(pin, GPIO.LOW)
        if self.pwm_a:
            self.pwm_a.ChangeDutyCycle(0)
        if self.pwm_b:
            self.pwm_b.ChangeDutyCycle(0)

    def cleanup(self):
        self.stop()
        if self.pwm_a:
            self.pwm_a.stop()
        if self.pwm_b:
            self.pwm_b.stop()
        GPIO.cleanup()

class HardwareUltrasonicHAL(UltrasonicHALBase):
    def __init__(self, pins: dict):
        if not GPIO_AVAILABLE:
            raise RuntimeError("RPi.GPIO is not available on this platform. Use mode: simulation.")

        self.pins = pins
        GPIO.setmode(GPIO.BCM)
        for s in ["front", "left", "right"]:
            trig = pins[f"{s}_trig"]
            echo = pins[f"{s}_echo"]
            GPIO.setup(trig, GPIO.OUT)
            GPIO.setup(echo, GPIO.IN)
            GPIO.output(trig, GPIO.LOW)
        time.sleep(0.05)

    def get_distance(self, sensor: str) -> float:
        trig = self.pins[f"{sensor}_trig"]
        echo = self.pins[f"{sensor}_echo"]

        # 10us trigger pulse
        GPIO.output(trig, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(trig, GPIO.LOW)

        pulse_start = time.time()
        pulse_end = time.time()
        timeout = pulse_start + 0.04  # 40ms timeout (~6.8 meters max)

        while GPIO.input(echo) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return 400.0  # Max distance fallback

        while GPIO.input(echo) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return 400.0

        pulse_duration = pulse_end - pulse_start
        # Speed of sound = 343 m/s = 34300 cm/s; distance = (time * speed) / 2
        distance = pulse_duration * 17150.0
        return round(distance, 1)

    def cleanup(self):
        GPIO.cleanup()

class HardwareGPSHAL(GPSHALBase):
    def __init__(self, port: str = "/dev/ttyAMA0", baudrate: int = 9600):
        self.ser = serial.Serial(port, baudrate, timeout=1.0)

    def read_fix(self) -> Tuple[Optional[float], Optional[float], float]:
        """Parses $GPRMC or $GPGGA NMEA sentences."""
        try:
            line = self.ser.readline().decode("ascii", errors="replace").strip()
            if line.startswith("$GPRMC"):
                parts = line.split(",")
                if len(parts) >= 8 and parts[2] == "A":  # Active fix
                    raw_lat, lat_dir = parts[3], parts[4]
                    raw_lon, lon_dir = parts[5], parts[6]
                    speed_knots = float(parts[7]) if parts[7] else 0.0

                    # Convert DDMM.MMMM to decimal degrees
                    lat = float(raw_lat[:2]) + float(raw_lat[2:]) / 60.0
                    if lat_dir == "S":
                        lat = -lat

                    lon = float(raw_lon[:3]) + float(raw_lon[3:]) / 60.0
                    if lon_dir == "W":
                        lon = -lon

                    speed_mps = speed_knots * 0.514444
                    return (round(lat, 6), round(lon, 6), round(speed_mps, 2))
        except Exception as e:
            logger.debug(f"GPS parsing error: {e}")
        return (None, None, 0.0)

class HardwareCameraHAL(CameraHALBase):
    def __init__(self, device_id: int = 0, width: int = 640, height: int = 480):
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV is not available.")
        self.cap = cv2.VideoCapture(device_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read_frame(self) -> Any:
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Camera frame read failed.")
            return None
        return frame

    def release(self):
        if self.cap:
            self.cap.release()

class HardwareSerialHAL(SerialHALBase):
    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200, timeout: float = 1.0):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)

    def write_line(self, line: str) -> bool:
        try:
            data = (line.rstrip() + "\n").encode("utf-8")
            self.ser.write(data)
            self.ser.flush()
            return True
        except Exception as e:
            logger.error(f"Serial write error: {e}")
            return False

    def read_line(self, timeout_sec: float = 1.0) -> Optional[str]:
        try:
            self.ser.timeout = timeout_sec
            line = self.ser.readline().decode("utf-8", errors="replace").strip()
            return line if line else None
        except Exception as e:
            logger.error(f"Serial read error: {e}")
            return None
