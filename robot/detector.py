import time
import math
import io
import base64
import random
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image

from robot.logger import logger

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class Deduplicator:
    """Filters duplicate detections within distance_threshold_m and time_window_sec."""
    def __init__(self, distance_threshold_m: float = 5.0, time_window_sec: float = 10.0):
        self.distance_threshold = distance_threshold_m
        self.time_window = time_window_sec
        # List of past detections: (hazard_class, lat, lon, timestamp)
        self.history: List[Tuple[str, float, float, float]] = []

    def is_duplicate(self, hazard_class: str, lat: float, lon: float, timestamp: float = None) -> bool:
        ts = timestamp or time.time()
        # Clean history older than time_window
        self.history = [h for h in self.history if (ts - h[3]) <= self.time_window]

        for prev_class, prev_lat, prev_lon, prev_ts in self.history:
            if prev_class.lower() == hazard_class.lower():
                dist = haversine_distance(lat, lon, prev_lat, prev_lon)
                if dist <= self.distance_threshold:
                    return True

        self.history.append((hazard_class.lower(), lat, lon, ts))
        return False

class HazardDetector:
    def __init__(
        self,
        model_path: str = "ml/weights/yolov8n.pt",
        confidence_threshold: float = 0.5,
        save_snapshot: bool = True,
        dedup_distance_m: float = 5.0,
        dedup_time_sec: float = 10.0
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.save_snapshot = save_snapshot
        self.deduplicator = Deduplicator(dedup_distance_m, dedup_time_sec)
        self.classes = {0: "pothole", 1: "crack", 2: "animal"}
        self.model = None

        self._init_model()

    def _init_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            logger.info(f"Loaded YOLOv8 model from {self.model_path}")
        except Exception as e:
            logger.warning(f"Ultralytics YOLO model unavailable ({e}). Initialized in synthetic detection mode.")
            self.model = None

    def detect(self, frame: Any, lat: float, lon: float) -> List[Dict[str, Any]]:
        """
        Runs inference on the frame.
        Returns list of valid, deduplicated hazards with bounding boxes and cropped base64 snapshot.
        """
        detections = []
        now = time.time()

        if self.model is not None:
            try:
                results = self.model.predict(frame, conf=self.confidence_threshold, verbose=False)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        hazard_class = self.classes.get(cls_id, "pothole")
                        xyxy = box.xyxy[0].tolist()

                        if self.deduplicator.is_duplicate(hazard_class, lat, lon, now):
                            logger.debug(f"Filtered duplicate hazard: {hazard_class} at ({lat}, {lon})")
                            continue

                        snap_b64 = self._crop_snapshot_base64(frame, xyxy) if self.save_snapshot else None
                        detections.append({
                            "hazard_class": hazard_class,
                            "confidence": round(conf, 3),
                            "bbox": {"x1": xyxy[0], "y1": xyxy[1], "x2": xyxy[2], "y2": xyxy[3]},
                            "snapshot_base64": snap_b64,
                            "latitude": lat,
                            "longitude": lon,
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
                        })
                return detections
            except Exception as e:
                logger.error(f"Inference error: {e}")

        # Synthetic fallback mode for laptop / test execution
        if random.random() < 0.25:  # 25% chance of hazard in test frame
            h_class = random.choice(["pothole", "crack", "animal"])
            conf = round(random.uniform(0.68, 0.94), 2)
            if not self.deduplicator.is_duplicate(h_class, lat, lon, now):
                snap_b64 = self._crop_snapshot_base64(frame, [80, 60, 240, 180]) if self.save_snapshot else None
                detections.append({
                    "hazard_class": h_class,
                    "confidence": conf,
                    "bbox": {"x1": 80.0, "y1": 60.0, "x2": 240.0, "y2": 180.0},
                    "snapshot_base64": snap_b64,
                    "latitude": lat,
                    "longitude": lon,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
                })

        return detections

    def _crop_snapshot_base64(self, frame: Any, bbox: List[float]) -> Optional[str]:
        """Crops hazard bounding box with margin, encodes as JPEG base64."""
        try:
            if isinstance(frame, Image.Image):
                img = frame
            else:
                # Convert OpenCV BGR to RGB PIL Image
                import cv2
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            w, h = img.size
            # Add 15% margin around bounding box
            x1, y1, x2, y2 = bbox
            bw, bh = x2 - x1, y2 - y1
            cx1 = max(0, int(x1 - bw * 0.15))
            cy1 = max(0, int(y1 - bh * 0.15))
            cx2 = min(w, int(x2 + bw * 0.15))
            cy2 = min(h, int(y2 + bh * 0.15))

            crop = img.crop((cx1, cy1, cx2, cy2))
            buffer = io.BytesIO()
            crop.save(buffer, format="JPEG", quality=80)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            logger.debug(f"Cropping snapshot error: {e}")
            return None
