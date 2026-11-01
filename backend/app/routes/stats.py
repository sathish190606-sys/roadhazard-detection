import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models import Hazard, RobotStatus
from backend.app.schemas import StatsResponse
from backend.app.routes.robots import ONLINE_TIMEOUT_SECONDS

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get("", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total_hazards = db.query(Hazard).count()

    # Breakdown by class
    classes = ["pothole", "crack", "animal"]
    by_class = {c: 0 for c in classes}
    class_counts = db.query(Hazard.hazard_class, func.count(Hazard.id)).group_by(Hazard.hazard_class).all()
    for hc, count in class_counts:
        by_class[hc] = count

    # Breakdown by status
    statuses = ["new", "acknowledged", "repaired"]
    by_status = {s: 0 for s in statuses}
    status_counts = db.query(Hazard.status, func.count(Hazard.id)).group_by(Hazard.status).all()
    for st, count in status_counts:
        by_status[st] = count

    # Average severity score
    avg_severity = db.query(func.avg(Hazard.severity_score)).scalar() or 0.0

    # Robot counts
    all_robots = db.query(RobotStatus).all()
    now = datetime.datetime.utcnow()
    active_robots = sum(
        1 for r in all_robots if (now - r.last_seen).total_seconds() < ONLINE_TIMEOUT_SECONDS
    )

    # Hazards per day (last 7 days)
    seven_days_ago = now - datetime.timedelta(days=7)
    recent_hazards = db.query(Hazard).filter(Hazard.created_at >= seven_days_ago).all()
    
    day_map = {}
    for i in range(7):
        d_str = (now - datetime.timedelta(days=6 - i)).strftime("%Y-%m-%d")
        day_map[d_str] = 0

    for h in recent_hazards:
        d_str = h.created_at.strftime("%Y-%m-%d")
        if d_str in day_map:
            day_map[d_str] += 1

    hazards_per_day = [{"date": d, "count": c} for d, c in day_map.items()]

    return StatsResponse(
        total_hazards=total_hazards,
        by_class=by_class,
        by_status=by_status,
        average_severity=round(float(avg_severity), 2),
        active_robots=active_robots,
        total_robots=len(all_robots),
        hazards_per_day=hazards_per_day
    )
