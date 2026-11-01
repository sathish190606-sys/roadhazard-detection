import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Road Hazard Robot Cloud Backend"
    API_V1_STR: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "super-secret-development-jwt-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ROBOT_API_KEY: str = "robot-sec-key-771ac-roadbot-edge-2026"
    
    # Database (Oracle PL/SQL, PostgreSQL, or SQLite)
    # Oracle Free / XE: "oracle+oracledb://roadbot:roadbot_pass@localhost:1521/?service_name=FREEPDB1"
    # PostgreSQL:       "postgresql+psycopg2://roadbot:roadbot_pass@localhost:5432/roadbot_db"
    # SQLite:           "sqlite:///./hazards.db"
    DATABASE_URL: str = "sqlite:///./hazards.db"
    
    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "roadbot-backend-subscriber"
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_HAZARD_TOPIC: str = "roadbot/+/hazards"
    MQTT_HEARTBEAT_TOPIC: str = "roadbot/+/heartbeat"
    
    # Severity & Alerts
    ALERT_SEVERITY_THRESHOLD: float = 75.0
    ALERT_RATE_LIMIT_MINUTES: int = 15
    
    # Email
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "alerts@example.com"
    SMTP_PASSWORD: str = "app-password"
    ALERT_RECIPIENT_EMAIL: str = "admin@example.com"
    
    # SMS (Twilio)
    TWILIO_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = "AC_dummy"
    TWILIO_AUTH_TOKEN: str = "dummy_token"
    TWILIO_FROM_NUMBER: str = "+1234567890"
    ALERT_RECIPIENT_SMS: str = "+19876543210"
    
    # Uploads directory for snapshots
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
