from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any

class MotorHALBase(ABC):
    @abstractmethod
    def forward(self, speed_pwm: int = 70):
        pass

    @abstractmethod
    def backward(self, speed_pwm: int = 50):
        pass

    @abstractmethod
    def turn_left(self, speed_pwm: int = 50):
        pass

    @abstractmethod
    def turn_right(self, speed_pwm: int = 50):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

class UltrasonicHALBase(ABC):
    @abstractmethod
    def get_distance(self, sensor: str) -> float:
        """Returns distance in centimeters for 'front', 'left', or 'right' sensor."""
        pass

    @abstractmethod
    def cleanup(self):
        pass

class GPSHALBase(ABC):
    @abstractmethod
    def read_fix(self) -> Tuple[Optional[float], Optional[float], float]:
        """Returns (latitude, longitude, speed_mps)."""
        pass

class CameraHALBase(ABC):
    @abstractmethod
    def read_frame(self) -> Any:
        """Returns BGR image numpy array or PIL Image."""
        pass

    @abstractmethod
    def release(self):
        pass

class SerialHALBase(ABC):
    @abstractmethod
    def write_line(self, line: str) -> bool:
        pass

    @abstractmethod
    def read_line(self, timeout_sec: float = 1.0) -> Optional[str]:
        pass
