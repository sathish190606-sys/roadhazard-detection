import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Sequence
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Hazard(Base):
    __tablename__ = "hazards"

    id = Column(Integer, Sequence("hazard_id_seq"), primary_key=True, index=True)
    robot_id = Column(String(50), index=True, nullable=False)
    hazard_class = Column(String(20), index=True, nullable=False)  # pothole, crack, animal
    confidence = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)
    snapshot_path = Column(String(255), nullable=True)
    repair_snapshot_path = Column(String(255), nullable=True)
    severity_score = Column(Float, default=50.0, index=True)
    cluster_count = Column(Integer, default=1)
    status = Column(String(20), default="new", index=True)  # new, acknowledged, repaired
    reported_by = Column(String(50), nullable=True)  # username of user who reported (null = robot-detected)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    alert_logs = relationship("AlertLog", back_populates="hazard", cascade="all, delete-orphan")

class RobotStatus(Base):
    __tablename__ = "robot_status"

    robot_id = Column(String(50), primary_key=True, index=True)
    status = Column(String(20), default="offline")  # online, offline, patrol, emergency_stop
    battery_percentage = Column(Float, default=100.0)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    speed = Column(Float, default=0.0)
    ip_address = Column(String(50), nullable=True)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="viewer")  # admin, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, Sequence("alert_log_id_seq"), primary_key=True, index=True)
    hazard_id = Column(Integer, ForeignKey("hazards.id"), nullable=False)
    channel = Column(String(20), nullable=False)  # email, sms
    recipient = Column(String(100), nullable=False)
    status = Column(String(20), default="sent")  # sent, failed, rate_limited
    message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)

    hazard = relationship("Hazard", back_populates="alert_logs")
