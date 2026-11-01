import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any

# Hazard Schemas
class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class HazardCreate(BaseModel):
    robot_id: str = Field(..., json_schema_extra={"example": "robot-01"})
    hazard_class: str = Field(..., json_schema_extra={"example": "pothole"})  # pothole, crack, animal
    confidence: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.88})
    latitude: float = Field(..., json_schema_extra={"example": 12.9716})
    longitude: float = Field(..., json_schema_extra={"example": 77.5946})
    bbox: Optional[BoundingBox] = None
    snapshot_base64: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None

class HazardUpdate(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "acknowledged"})  # new, acknowledged, repaired

class HazardResponse(BaseModel):
    id: int
    robot_id: str
    hazard_class: str
    confidence: float
    latitude: float
    longitude: float
    bbox_x1: Optional[float] = None
    bbox_y1: Optional[float] = None
    bbox_x2: Optional[float] = None
    bbox_y2: Optional[float] = None
    snapshot_url: Optional[str] = None
    repair_snapshot_url: Optional[str] = None
    severity_score: float
    cluster_count: int
    status: str
    reported_by: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# Robot Heartbeat / Status Schemas
class RobotHeartbeat(BaseModel):
    robot_id: str
    status: str = "online"  # online, patrol, idle, emergency_stop
    battery_percentage: float = 100.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: float = 0.0
    ip_address: Optional[str] = None

class RobotStatusResponse(BaseModel):
    robot_id: str
    status: str
    battery_percentage: float
    current_latitude: Optional[float]
    current_longitude: Optional[float]
    speed: float
    ip_address: Optional[str]
    last_seen: datetime.datetime
    is_online: bool

    model_config = ConfigDict(from_attributes=True)

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserHazardReport(BaseModel):
    """Schema for normal users reporting a pothole from the map."""
    hazard_class: str = Field(default="pothole", json_schema_extra={"example": "pothole"})
    latitude: float = Field(..., json_schema_extra={"example": 12.9716})
    longitude: float = Field(..., json_schema_extra={"example": 77.5946})
    description: Optional[str] = Field(None, json_schema_extra={"example": "Large pothole near main road"})
    snapshot_base64: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

# Stats Schemas
class StatsResponse(BaseModel):
    total_hazards: int
    by_class: Dict[str, int]
    by_status: Dict[str, int]
    average_severity: float
    active_robots: int
    total_robots: int
    hazards_per_day: List[Dict[str, Any]]
