from typing import Dict
from statistics import median
from robot.hal.base import UltrasonicHALBase

class UltrasonicManager:
    def __init__(self, hal: UltrasonicHALBase):
        self.hal = hal

    def read_distance(self, sensor: str, samples: int = 3) -> float:
        """Reads sensor distance multiple times and returns median to filter noise."""
        readings = []
        for _ in range(samples):
            dist = self.hal.get_distance(sensor)
            readings.append(dist)
        return round(float(median(readings)), 1)

    def read_all_distances(self) -> Dict[str, float]:
        """Returns distance dict: {'front': cm, 'left': cm, 'right': cm}."""
        return {
            "front": self.read_distance("front"),
            "left": self.read_distance("left"),
            "right": self.read_distance("right"),
        }
