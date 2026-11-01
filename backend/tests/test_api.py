import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.config import settings

# Test in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_temp.db"):
        try:
            os.remove("./test_temp.db")
        except Exception:
            pass

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_auth_registration_and_login():
    reg_resp = client.post("/api/auth/register", json={
        "username": "patrol_admin",
        "password": "strongpassword123",
        "role": "admin"
    })
    assert reg_resp.status_code == 200
    assert reg_resp.json()["username"] == "patrol_admin"

    login_resp = client.post("/api/auth/login", json={
        "username": "patrol_admin",
        "password": "strongpassword123"
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["role"] == "admin"

def test_create_hazard_with_robot_key():
    headers = {"X-Robot-Key": settings.ROBOT_API_KEY}
    payload = {
        "robot_id": "robot-alpha",
        "hazard_class": "pothole",
        "confidence": 0.85,
        "latitude": 12.9715987,
        "longitude": 77.5945627,
        "bbox": {"x1": 100.0, "y1": 150.0, "x2": 200.0, "y2": 250.0}
    }
    response = client.post("/api/hazards", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["hazard_class"] == "pothole"
    assert data["robot_id"] == "robot-alpha"
    assert data["severity_score"] > 50.0
    assert data["status"] == "new"

def test_get_hazards_filtering():
    response = client.get("/api/hazards?hazard_class=pothole")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert items[0]["hazard_class"] == "pothole"

def test_patch_hazard_status():
    # Login as admin to get auth headers
    login_resp = client.post("/api/auth/login", json={
        "username": "patrol_admin",
        "password": "strongpassword123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch first hazard
    hazards = client.get("/api/hazards").json()
    hazard_id = hazards[0]["id"]

    patch_resp = client.patch(f"/api/hazards/{hazard_id}", json={"status": "acknowledged"}, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "acknowledged"

def test_robot_heartbeat_and_status():
    headers = {"X-Robot-Key": settings.ROBOT_API_KEY}
    hb_payload = {
        "robot_id": "robot-alpha",
        "status": "patrol",
        "battery_percentage": 88.5,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "speed": 1.2
    }
    response = client.post("/api/robots/heartbeat", json=hb_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["battery_percentage"] == 88.5

    status_resp = client.get("/api/robots/status")
    assert status_resp.status_code == 200
    robots = status_resp.json()
    assert len(robots) >= 1
    assert robots[0]["is_online"] is True

def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_hazards" in stats
    assert stats["total_hazards"] >= 1
    assert "by_class" in stats
    assert "hazards_per_day" in stats
