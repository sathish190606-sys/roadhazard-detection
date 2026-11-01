import os
import sys
import json
import time
import math
import random
import base64
import io
import argparse
import logging
from typing import List, Tuple
from PIL import Image, ImageDraw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [SIM] %(message)s")
logger = logging.getLogger("simulator")

def generate_synthetic_hazard_image(hazard_class: str, confidence: float) -> str:
    """Generates a synthetic camera snapshot with drawn road hazard and bounding box, returning base64 string."""
    width, height = 320, 240
    # Road surface background (asphalt texture gray/dark)
    img = Image.new("RGB", (width, height), color=(45, 47, 50))
    draw = ImageDraw.Draw(img)

    # Road lane markings
    draw.line([(0, 20), (width, 20)], fill=(200, 200, 200), width=3)
    draw.line([(0, 220), (width, 220)], fill=(200, 200, 200), width=3)
    for x in range(0, width, 40):
        draw.line([(x, 120), (x + 20, 120)], fill=(220, 180, 0), width=2)

    # Hazard drawing based on class
    cx, cy = random.randint(100, 220), random.randint(60, 180)
    if hazard_class == "pothole":
        # Dark depressed crater with asphalt fracture ring
        draw.ellipse([cx - 35, cy - 25, cx + 35, cy + 25], fill=(20, 20, 22), outline=(70, 70, 75), width=3)
        draw.ellipse([cx - 20, cy - 15, cx + 20, cy + 15], fill=(10, 10, 12))
    elif hazard_class == "crack":
        # Jagged fracture lines
        points = [(cx - 40, cy - 20), (cx - 20, cy - 5), (cx - 5, cy + 10), (cx + 15, cy - 10), (cx + 35, cy + 20)]
        draw.line(points, fill=(15, 15, 18), width=4)
        draw.line([(p[0] + 5, p[1] + 5) for p in points], fill=(60, 60, 65), width=2)
    elif hazard_class == "animal":
        # Animal silhouette / obstacle
        draw.ellipse([cx - 20, cy - 15, cx + 20, cy + 15], fill=(139, 69, 19))
        draw.ellipse([cx + 12, cy - 25, cx + 28, cy - 10], fill=(160, 82, 45))  # head
        draw.polygon([(cx + 18, cy - 30), (cx + 22, cy - 24), (cx + 26, cy - 30)], fill=(139, 69, 19))

    # YOLO Bounding Box overlay
    bx1, by1 = max(10, cx - 45), max(10, cy - 35)
    bx2, by2 = min(width - 10, cx + 45), min(height - 10, cy + 35)
    color = (255, 69, 58) if hazard_class == "pothole" else ((255, 159, 10) if hazard_class == "crack" else (48, 209, 88))
    draw.rectangle([bx1, by1, bx2, by2], outline=color, width=2)
    draw.text((bx1 + 3, by1 - 14), f"{hazard_class.upper()} {confidence:.2f}", fill=color)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

class RouteSimulator:
    def __init__(
        self,
        geojson_path: str,
        robot_id: str = "robot-01",
        backend_url: str = "http://localhost:8000",
        broker_host: str = "localhost",
        broker_port: int = 1883,
        api_key: str = "robot-sec-key-771ac-roadbot-edge-2026",
        mode: str = "auto",
        speed_multiplier: float = 1.0,
        hazard_interval: float = 8.0,
    ):
        self.geojson_path = geojson_path
        self.robot_id = robot_id
        self.backend_url = backend_url.rstrip("/")
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.api_key = api_key
        self.mode = mode
        self.speed_multiplier = speed_multiplier
        self.hazard_interval = hazard_interval

        self.waypoints = self._load_waypoints()
        self.current_idx = 0
        self.battery = 98.5
        self.mqtt_client = None
        self.using_mqtt = False

        self._init_network()

    def _load_waypoints(self) -> List[Tuple[float, float]]:
        if not os.path.exists(self.geojson_path):
            logger.warning(f"GeoJSON not found at {self.geojson_path}, generating synthetic circular circuit.")
            center_lat, center_lon = 12.9716, 77.5946
            pts = []
            for angle in range(0, 360, 15):
                rad = math.radians(angle)
                lat = center_lat + 0.0015 * math.sin(rad)
                lon = center_lon + 0.0015 * math.cos(rad)
                pts.append((lat, lon))
            return pts

        with open(self.geojson_path, "r") as f:
            data = json.load(f)
        coords = data["features"][0]["geometry"]["coordinates"]
        # GeoJSON is [lon, lat], convert to (lat, lon)
        return [(c[1], c[0]) for c in coords]

    def _init_network(self):
        if self.mode in ["mqtt", "auto"]:
            try:
                import paho.mqtt.client as mqtt
                try:
                    self.mqtt_client = mqtt.Client(
                        mqtt.CallbackAPIVersion.VERSION2,
                        client_id=f"sim-{self.robot_id}-{random.randint(100,999)}"
                    )
                except Exception:
                    self.mqtt_client = mqtt.Client(client_id=f"sim-{self.robot_id}")

                self.mqtt_client.connect(self.broker_host, self.broker_port, keepalive=60)
                self.mqtt_client.loop_start()
                self.using_mqtt = True
                logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            except Exception as e:
                logger.warning(f"Could not connect via MQTT ({e}). Falling back to HTTP.")
                self.using_mqtt = False

        if not self.using_mqtt:
            logger.info(f"Using HTTP REST uplink at {self.backend_url}/api")

    def send_heartbeat(self, lat: float, lon: float, speed: float):
        payload = {
            "robot_id": self.robot_id,
            "status": "patrol",
            "battery_percentage": round(self.battery, 1),
            "latitude": lat,
            "longitude": lon,
            "speed": round(speed, 2),
            "ip_address": "192.168.1.105"
        }

        if self.using_mqtt and self.mqtt_client:
            topic = f"roadbot/{self.robot_id}/heartbeat"
            self.mqtt_client.publish(topic, json.dumps(payload))
            logger.debug(f"Heartbeat sent via MQTT to {topic}")
        else:
            try:
                import requests
                headers = {"X-Robot-Key": self.api_key}
                requests.post(f"{self.backend_url}/api/robots/heartbeat", json=payload, headers=headers, timeout=2.0)
            except Exception as e:
                logger.debug(f"Heartbeat HTTP error: {e}")

    def send_hazard(self, hazard_class: str, confidence: float, lat: float, lon: float):
        snapshot_b64 = generate_synthetic_hazard_image(hazard_class, confidence)
        payload = {
            "robot_id": self.robot_id,
            "hazard_class": hazard_class,
            "confidence": round(confidence, 3),
            "latitude": round(lat, 7),
            "longitude": round(lon, 7),
            "bbox": {"x1": 80.0, "y1": 60.0, "x2": 240.0, "y2": 180.0},
            "snapshot_base64": snapshot_b64
        }

        if self.using_mqtt and self.mqtt_client:
            topic = f"roadbot/{self.robot_id}/hazards"
            self.mqtt_client.publish(topic, json.dumps(payload))
            logger.info(f"🚨 Hazard ({hazard_class}, {confidence:.2f}) published via MQTT to {topic}")
        else:
            try:
                import requests
                headers = {"X-Robot-Key": self.api_key}
                resp = requests.post(f"{self.backend_url}/api/hazards", json=payload, headers=headers, timeout=3.0)
                if resp.status_code == 201:
                    data = resp.json()
                    logger.info(f"🚨 Hazard ({hazard_class}, {confidence:.2f}) posted via HTTP! ID: {data['id']}, Severity: {data['severity_score']}")
                else:
                    logger.warning(f"Hazard POST failed: {resp.status_code} {resp.text}")
            except Exception as e:
                logger.error(f"Hazard HTTP request error: {e}")

    def run(self, max_iterations: int = 0):
        logger.info(f"Starting patrol route simulation with {len(self.waypoints)} waypoints...")
        classes = ["pothole", "pothole", "crack", "pothole", "animal", "crack"]
        last_hazard_time = time.time()
        iterations = 0

        try:
            while True:
                curr_lat, curr_lon = self.waypoints[self.current_idx]
                next_lat, next_lon = self.waypoints[(self.current_idx + 1) % len(self.waypoints)]

                # Micro-steps between waypoints
                steps = 5
                for step in range(steps):
                    alpha = step / float(steps)
                    lat = curr_lat + alpha * (next_lat - curr_lat) + (random.uniform(-0.00002, 0.00002))
                    lon = curr_lon + alpha * (next_lon - curr_lon) + (random.uniform(-0.00002, 0.00002))
                    speed = 1.2 * self.speed_multiplier + random.uniform(-0.1, 0.1)

                    # Send telemetry heartbeat
                    self.send_heartbeat(lat, lon, speed)

                    # Check hazard trigger
                    now = time.time()
                    if now - last_hazard_time >= self.hazard_interval:
                        hazard_type = random.choice(classes)
                        confidence = random.uniform(0.75, 0.96)
                        self.send_hazard(hazard_type, confidence, lat, lon)
                        last_hazard_time = now

                    # Battery discharge
                    self.battery = max(5.0, self.battery - 0.01)

                    sleep_dur = max(0.2, 1.0 / self.speed_multiplier)
                    time.sleep(sleep_dur)

                self.current_idx = (self.current_idx + 1) % len(self.waypoints)
                iterations += 1

                if max_iterations > 0 and iterations >= max_iterations:
                    logger.info(f"Completed {iterations} waypoint circuits. Stopping simulator.")
                    break
        except KeyboardInterrupt:
            logger.info("Simulation halted by user.")
        finally:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()

def main():
    parser = argparse.ArgumentParser(description="Road Hazard Robot Route & Telemetry Simulator")
    parser.add_argument("--geojson", default="simulator/campus_route.geojson", help="Path to GeoJSON route")
    parser.add_argument("--robot-id", default="robot-01", help="Identifier of simulated robot")
    parser.add_argument("--speed", type=float, default=1.0, help="Simulation speed multiplier")
    parser.add_argument("--interval", type=float, default=6.0, help="Hazard event interval in seconds")
    parser.add_argument("--mode", default="auto", choices=["auto", "mqtt", "http"], help="Uplink transmission protocol")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="FastAPI backend URL")
    parser.add_argument("--broker-host", default="localhost", help="Mosquitto broker hostname")
    parser.add_argument("--broker-port", type=int, default=1883, help="Mosquitto broker port")
    parser.add_argument("--api-key", default="robot-sec-key-771ac-roadbot-edge-2026", help="Robot API authentication key")
    parser.add_argument("--max-steps", type=int, default=0, help="Max iterations (0 = infinite)")
    args = parser.parse_args()

    sim = RouteSimulator(
        geojson_path=args.geojson,
        robot_id=args.robot_id,
        backend_url=args.backend_url,
        broker_host=args.broker_host,
        broker_port=args.broker_port,
        api_key=args.api_key,
        mode=args.mode,
        speed_multiplier=args.speed,
        hazard_interval=args.interval,
    )
    sim.run(max_iterations=args.max_steps)

if __name__ == "__main__":
    main()
