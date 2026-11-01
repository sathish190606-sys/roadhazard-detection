import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import RobotStatus
from backend.app.schemas import RobotHeartbeat, RobotStatusResponse
from backend.app.websocket_manager import ws_manager
from backend.app.routes.auth import verify_robot_auth

router = APIRouter(prefix="/robots", tags=["Robots"])

ONLINE_TIMEOUT_SECONDS = 30

def format_robot_response(r: RobotStatus) -> RobotStatusResponse:
    now = datetime.datetime.utcnow()
    is_online = (now - r.last_seen).total_seconds() < ONLINE_TIMEOUT_SECONDS
    return RobotStatusResponse(
        robot_id=r.robot_id,
        status=r.status if is_online else "offline",
        battery_percentage=r.battery_percentage,
        current_latitude=r.current_latitude,
        current_longitude=r.current_longitude,
        speed=r.speed,
        ip_address=r.ip_address,
        last_seen=r.last_seen,
        is_online=is_online
    )

@router.post("/heartbeat", response_model=RobotStatusResponse)
async def record_heartbeat(
    hb: RobotHeartbeat,
    auth=Depends(verify_robot_auth),
    db: Session = Depends(get_db)
):
    robot = db.query(RobotStatus).filter(RobotStatus.robot_id == hb.robot_id).first()
    now = datetime.datetime.utcnow()

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
    await ws_manager.broadcast({
        "type": "ROBOT_HEARTBEAT",
        "data": res.model_dump()
    })
    return res

@router.get("/status", response_model=List[RobotStatusResponse])
def get_all_robot_statuses(db: Session = Depends(get_db)):
    robots = db.query(RobotStatus).all()
    return [format_robot_response(r) for r in robots]
