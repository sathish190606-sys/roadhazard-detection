from typing import Any
from robot.hal.base import CameraHALBase

class CameraManager:
    def __init__(self, hal: CameraHALBase):
        self.hal = hal

    def capture_frame(self) -> Any:
        return self.hal.read_frame()

    def release(self):
        self.hal.release()
