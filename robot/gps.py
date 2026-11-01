from typing import Optional, Tuple
from robot.hal.base import GPSHALBase

class GPSManager:
    def __init__(self, hal: GPSHALBase):
        self.hal = hal
        self.last_known_lat: Optional[float] = None
        self.last_known_lon: Optional[float] = None
        self.last_known_speed: float = 0.0

    def get_coordinates(self) -> Tuple[Optional[float], Optional[float], float]:
        lat, lon, spd = self.hal.read_fix()
        if lat is not None and lon is not None:
            self.last_known_lat = lat
            self.last_known_lon = lon
            self.last_known_speed = spd
        return (self.last_known_lat, self.last_known_lon, self.last_known_speed)
