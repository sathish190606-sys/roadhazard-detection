#!/usr/bin/env python3
"""
Seed realistic road hazards and robot telemetry for dashboard demo.
"""
import sys
import os
import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.database import engine, Base, SessionLocal
from backend.app.models import Hazard, RobotStatus, User
from backend.app.routes.auth import get_password_hash

def seed_demo_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Admin user
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin"
            )
            db.add(admin)

        # 2. Robot Status
        robot = db.query(RobotStatus).filter(RobotStatus.robot_id == "robot-01").first()
        if not robot:
            robot = RobotStatus(
                robot_id="robot-01",
                status="patrol",
                battery_percentage=89.5,
                current_latitude=12.97185,
                current_longitude=77.59472,
                speed=1.4,
                ip_address="192.168.1.145",
                last_seen=datetime.datetime.utcnow()
            )
            db.add(robot)
        else:
            robot.status = "patrol"
            robot.battery_percentage = 89.5
            robot.last_seen = datetime.datetime.utcnow()

        # 3. Hazards along route
        existing_count = db.query(Hazard).count()
        if existing_count == 0:
            demo_hazards = [
                {
                    "robot_id": "robot-01",
                    "hazard_class": "pothole",
                    "confidence": 0.94,
                    "latitude": 12.97165,
                    "longitude": 77.59462,
                    "bbox_x1": 120.0, "bbox_y1": 200.0, "bbox_x2": 310.0, "bbox_y2": 380.0,
                    "severity_score": 88.5,
                    "cluster_count": 3,
                    "status": "new",
                    "created_at": datetime.datetime.utcnow() - datetime.timedelta(minutes=12)
                },
                {
                    "robot_id": "robot-01",
                    "hazard_class": "crack",
                    "confidence": 0.88,
                    "latitude": 12.97210,
                    "longitude": 77.59570,
                    "bbox_x1": 80.0, "bbox_y1": 150.0, "bbox_x2": 450.0, "bbox_y2": 260.0,
                    "severity_score": 64.2,
                    "cluster_count": 1,
                    "status": "acknowledged",
                    "created_at": datetime.datetime.utcnow() - datetime.timedelta(minutes=25)
                },
                {
                    "robot_id": "robot-01",
                    "hazard_class": "animal",
                    "confidence": 0.91,
                    "latitude": 12.97275,
                    "longitude": 77.59580,
                    "bbox_x1": 210.0, "bbox_y1": 140.0, "bbox_x2": 390.0, "bbox_y2": 320.0,
                    "severity_score": 92.0,
                    "cluster_count": 1,
                    "status": "new",
                    "created_at": datetime.datetime.utcnow() - datetime.timedelta(minutes=4)
                },
                {
                    "robot_id": "robot-01",
                    "hazard_class": "pothole",
                    "confidence": 0.82,
                    "latitude": 12.97330,
                    "longitude": 77.59500,
                    "bbox_x1": 150.0, "bbox_y1": 220.0, "bbox_x2": 280.0, "bbox_y2": 350.0,
                    "severity_score": 76.8,
                    "cluster_count": 2,
                    "status": "new",
                    "created_at": datetime.datetime.utcnow() - datetime.timedelta(minutes=38)
                },
                {
                    "robot_id": "robot-01",
                    "hazard_class": "crack",
                    "confidence": 0.79,
                    "latitude": 12.97310,
                    "longitude": 77.59385,
                    "bbox_x1": 100.0, "bbox_y1": 180.0, "bbox_x2": 380.0, "bbox_y2": 290.0,
                    "severity_score": 52.4,
                    "cluster_count": 1,
                    "status": "repaired",
                    "created_at": datetime.datetime.utcnow() - datetime.timedelta(hours=2)
                },
                {
                    "robot_id": "robot-01",
                    "hazard_class": "pothole",
                    "confidence": 0.96,
                    "latitude": 12.97205,
                    "longitude": 77.59360,
                    "bbox_x1": 160.0, "bbox_y1": 190.0, "bbox_x2": 340.0, "bbox_y2": 370.0,
                    "severity_score": 91.2,
                    "cluster_count": 4,
                    "status": "new",
                    "created_at": datetime.datetime.utcnow() - datetime.timedelta(minutes=8)
                },
                {
                    "robot_id": "robot-01",
                    "hazard_class": "crack",
                    "confidence": 0.85,
                    "latitude": 12.97175,
                    "longitude": 77.59510,
                    "bbox_x1": 90.0, "bbox_y1": 140.0, "bbox_x2": 420.0, "bbox_y2": 270.0,
                    "severity_score": 68.0,
                    "cluster_count": 2,
                    "status": "repaired",
                    "created_at": datetime.datetime.utcnow() - datetime.timedelta(hours=5)
                }
            ]

            for h in demo_hazards:
                hazard_obj = Hazard(**h)
                db.add(hazard_obj)

        db.commit()
        print("[SUCCESS] Demo data seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
