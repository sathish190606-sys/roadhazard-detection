import json
import logging
import asyncio
# pyrefly: ignore [missing-import]
import paho.mqtt.client as mqtt
from typing import Optional

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.schemas import HazardCreate, RobotHeartbeat
from backend.app.models import Hazard, RobotStatus
from backend.app.scoring import find_nearby_cluster, calculate_severity_score
from backend.app.alerts import trigger_alerts_if_eligible
from backend.app.websocket_manager import ws_manager
from backend.app.routes.hazards import save_base64_image, format_hazard_response
from backend.app.routes.robots import format_robot_response

logger = logging.getLogger(__name__)

class MQTTSubscriber:
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_connected = False

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            client.subscribe(settings.MQTT_HAZARD_TOPIC)
            client.subscribe(settings.MQTT_HEARTBEAT_TOPIC)
            logger.info(f"Subscribed to topics: {settings.MQTT_HAZARD_TOPIC}, {settings.MQTT_HEARTBEAT_TOPIC}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def on_disconnect(self, client, userdata, rc, properties=None):
        self.is_connected = False
        logger.warning(f"Disconnected from MQTT broker (rc: {rc})")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")
        logger.info(f"Received MQTT message on topic '{topic}'")

        try:
            data = json.loads(payload_str)
        except Exception as e:
            logger.error(f"Failed to parse MQTT JSON payload: {e}")
            return

        # Extract robot_id from topic (e.g. roadbot/robot-01/hazards)
        topic_parts = topic.split("/")
        robot_id_from_topic = topic_parts[1] if len(topic_parts) >= 2 else "unknown-robot"

        if "hazards" in topic:
            self._handle_hazard_message(data, robot_id_from_topic)
        elif "heartbeat" in topic:
            self._handle_heartbeat_message(data, robot_id_from_topic)

    def _handle_hazard_message(self, data: dict, robot_id_from_topic: str):
        if "robot_id" not in data:
            data["robot_id"] = robot_id_from_topic

        try:
            hazard_in = HazardCreate(**data)
        except Exception as e:
            logger.error(f"MQTT Hazard payload validation error: {e}")
            return

        db = SessionLocal()
        try:
            snapshot_path = None
            if hazard_in.snapshot_base64:
                snapshot_path = save_base64_image(hazard_in.snapshot_base64)

            cluster_count, _ = find_nearby_cluster(
                db,
                hazard_in.latitude,
                hazard_in.longitude,
                hazard_in.hazard_class,
                radius_meters=15.0
            )
            severity = calculate_severity_score(
                hazard_in.hazard_class,
                hazard_in.confidence,
                cluster_count=cluster_count
            )

            bbox_x1 = hazard_in.bbox.x1 if hazard_in.bbox else None
            bbox_y1 = hazard_in.bbox.y1 if hazard_in.bbox else None
            bbox_x2 = hazard_in.bbox.x2 if hazard_in.bbox else None
            bbox_y2 = hazard_in.bbox.y2 if hazard_in.bbox else None

            hazard = Hazard(
                robot_id=hazard_in.robot_id,
                hazard_class=hazard_in.hazard_class.lower(),
                confidence=hazard_in.confidence,
                latitude=hazard_in.latitude,
                longitude=hazard_in.longitude,
                bbox_x1=bbox_x1,
                bbox_y1=bbox_y1,
                bbox_x2=bbox_x2,
                bbox_y2=bbox_y2,
                snapshot_path=snapshot_path,
                severity_score=severity,
                cluster_count=cluster_count,
                status="new"
            )
            db.add(hazard)
            db.commit()
            db.refresh(hazard)

            trigger_alerts_if_eligible(hazard, db)
            res = format_hazard_response(hazard)

            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast({"type": "NEW_HAZARD", "data": res.model_dump()}),
                    self.loop
                )
        except Exception as e:
            logger.error(f"Error persisting MQTT hazard: {e}")
            db.rollback()
        finally:
            db.close()

    def _handle_heartbeat_message(self, data: dict, robot_id_from_topic: str):
        if "robot_id" not in data:
            data["robot_id"] = robot_id_from_topic

        try:
            hb = RobotHeartbeat(**data)
        except Exception as e:
            logger.error(f"MQTT Heartbeat payload validation error: {e}")
            return

        db = SessionLocal()
        try:
            import datetime
            now = datetime.datetime.utcnow()
            robot = db.query(RobotStatus).filter(RobotStatus.robot_id == hb.robot_id).first()
            if not robot:
                robot = RobotStatus(
                    robot_id=hb.robot_id,
                    status=hb.status,
                    battery_percentage=hb.battery_percentage,
                    current_latitude=hb.latitude,
                    current_longitude=hb.longitude,
                    speed=hb.speed,
                    ip_address=hb.ip_address,
                    last_seen=now
                )
                db.add(robot)
            else:
                robot.status = hb.status
                robot.battery_percentage = hb.battery_percentage
                if hb.latitude is not None:
                    robot.current_latitude = hb.latitude
                if hb.longitude is not None:
                    robot.current_longitude = hb.longitude
                robot.speed = hb.speed
                if hb.ip_address:
                    robot.ip_address = hb.ip_address
                robot.last_seen = now

            db.commit()
            db.refresh(robot)

            res = format_robot_response(robot)
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast({"type": "ROBOT_HEARTBEAT", "data": res.model_dump()}),
                    self.loop
                )
        except Exception as e:
            logger.error(f"Error persisting MQTT heartbeat: {e}")
            db.rollback()
        finally:
            db.close()

    def start(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        try:
            # paho-mqtt v2 Client initialization
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=settings.MQTT_CLIENT_ID
            )
        except Exception:
            self.client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)

        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        try:
            logger.info(f"Connecting to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}...")
            self.client.connect_async(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.warning(f"Could not connect to MQTT broker ({e}). Will retry in background.")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client stopped.")

mqtt_subscriber = MQTTSubscriber()
