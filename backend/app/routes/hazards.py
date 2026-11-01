import base64
import os
import uuid
import datetime
import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import Hazard
from backend.app.schemas import HazardCreate, HazardResponse, HazardUpdate, UserHazardReport
from backend.app.scoring import find_nearby_cluster, calculate_severity_score
from backend.app.alerts import trigger_alerts_if_eligible
from backend.app.websocket_manager import ws_manager
from backend.app.routes.auth import verify_robot_auth, get_current_user, require_admin

router = APIRouter(prefix="/hazards", tags=["Hazards"])

def save_base64_image(base64_data: str) -> Optional[str]:
    """Decodes base64 string and saves it to uploads directory, returning relative path."""
    try:
        # Strip data URL prefix if present
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        image_bytes = base64.b64decode(base64_data)
        filename = f"hazard_{uuid.uuid4().hex[:12]}.jpg"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return f"/uploads/{filename}"
    except Exception as e:
        print(f"Error saving snapshot image: {e}")
        return None

def format_hazard_response(h: Hazard) -> HazardResponse:
    return HazardResponse(
        id=h.id,
        robot_id=h.robot_id,
        hazard_class=h.hazard_class,
        confidence=h.confidence,
        latitude=h.latitude,
        longitude=h.longitude,
        bbox_x1=h.bbox_x1,
        bbox_y1=h.bbox_y1,
        bbox_x2=h.bbox_x2,
        bbox_y2=h.bbox_y2,
        snapshot_url=h.snapshot_path,
        repair_snapshot_url=h.repair_snapshot_path,
        severity_score=h.severity_score,
        cluster_count=h.cluster_count,
        status=h.status,
        reported_by=h.reported_by,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )

@router.post("", response_model=HazardResponse, status_code=status.HTTP_201_CREATED)
async def create_hazard(
    hazard_in: HazardCreate,
    auth=Depends(verify_robot_auth),
    db: Session = Depends(get_db)
):
    snapshot_path = None
    if hazard_in.snapshot_base64:
        snapshot_path = save_base64_image(hazard_in.snapshot_base64)

    # Calculate cluster count and severity
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
        status="new",
        created_at=hazard_in.timestamp or datetime.datetime.utcnow()
    )
    db.add(hazard)
    db.commit()
    db.refresh(hazard)

    # Evaluate alerts
    trigger_alerts_if_eligible(hazard, db)

    # Broadcast live update
    res = format_hazard_response(hazard)
    await ws_manager.broadcast({
        "type": "NEW_HAZARD",
        "data": res.model_dump()
    })

    return res

@router.get("", response_model=List[HazardResponse])
def get_hazards(
    hazard_class: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    min_confidence: Optional[float] = None,
    min_severity: Optional[float] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Hazard)
    if hazard_class:
        query = query.filter(Hazard.hazard_class == hazard_class.lower())
    if status_filter:
        query = query.filter(Hazard.status == status_filter.lower())
    if min_confidence is not None:
        query = query.filter(Hazard.confidence >= min_confidence)
    if min_severity is not None:
        query = query.filter(Hazard.severity_score >= min_severity)
    if start_date:
        query = query.filter(Hazard.created_at >= start_date)
    if end_date:
        query = query.filter(Hazard.created_at <= end_date)
    if min_lat is not None and max_lat is not None:
        query = query.filter(Hazard.latitude.between(min_lat, max_lat))
    if min_lon is not None and max_lon is not None:
        query = query.filter(Hazard.longitude.between(min_lon, max_lon))

    hazards = query.order_by(Hazard.created_at.desc()).offset(offset).limit(limit).all()
    return [format_hazard_response(h) for h in hazards]

@router.get("/export/csv")
def export_hazards_csv(
    hazard_class: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    """Download full hazard reports as a CSV spreadsheet."""
    query = db.query(Hazard)
    if hazard_class:
        query = query.filter(Hazard.hazard_class == hazard_class.lower())
    if status_filter:
        query = query.filter(Hazard.status == status_filter.lower())
    hazards = query.order_by(Hazard.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Robot / Reporter", "Class", "Confidence", "Latitude", "Longitude", "Severity Score", "Sightings", "Status", "Reported At"])
    for h in hazards:
        writer.writerow([
            h.id,
            h.reported_by or h.robot_id,
            h.hazard_class,
            f"{h.confidence * 100:.1f}%",
            h.latitude,
            h.longitude,
            h.severity_score,
            h.cluster_count,
            h.status,
            h.created_at.strftime("%Y-%m-%d %H:%M:%S") if h.created_at else ""
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hazards_report.csv"}
    )

@router.get("/{hazard_id}", response_model=HazardResponse)
def get_hazard(hazard_id: int, db: Session = Depends(get_db)):
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
    return format_hazard_response(hazard)

@router.patch("/{hazard_id}", response_model=HazardResponse)
async def update_hazard_status(
    hazard_id: int,
    update_data: HazardUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")

    valid_statuses = ["new", "acknowledged", "repaired"]
    new_status = update_data.status.lower()
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    # Only admins can mark hazards as repaired
    if new_status == "repaired" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can mark hazards as repaired")

    hazard.status = new_status
    hazard.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(hazard)

    res = format_hazard_response(hazard)
    await ws_manager.broadcast({
        "type": "HAZARD_UPDATED",
        "data": res.model_dump()
    })
    return res


@router.post("/report", response_model=HazardResponse, status_code=status.HTTP_201_CREATED)
async def user_report_hazard(
    report: UserHazardReport,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow authenticated users to report a pothole/hazard from the map."""
    snapshot_path = None
    if report.snapshot_base64:
        snapshot_path = save_base64_image(report.snapshot_base64)

    # Calculate cluster info
    cluster_count, _ = find_nearby_cluster(
        db,
        report.latitude,
        report.longitude,
        report.hazard_class,
        radius_meters=15.0
    )
    severity = calculate_severity_score(
        report.hazard_class,
        0.85,  # default confidence for user reports
        cluster_count=cluster_count
    )

    hazard = Hazard(
        robot_id=f"user:{current_user.username}",
        hazard_class=report.hazard_class.lower(),
        confidence=0.85,
        latitude=report.latitude,
        longitude=report.longitude,
        snapshot_path=snapshot_path,
        severity_score=severity,
        cluster_count=cluster_count,
        status="new",
        reported_by=current_user.username,
        created_at=datetime.datetime.utcnow()
    )
    db.add(hazard)
    db.commit()
    db.refresh(hazard)

    # Evaluate alerts
    trigger_alerts_if_eligible(hazard, db)

    # Broadcast live update
    res = format_hazard_response(hazard)
    await ws_manager.broadcast({
        "type": "NEW_HAZARD",
        "data": res.model_dump()
    })

    return res


@router.delete("/{hazard_id}", status_code=status.HTTP_200_OK)
async def delete_hazard(
    hazard_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: delete a fake or invalid hazard report."""
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")

    # If snapshot exists on disk, clean it up
    if hazard.snapshot_path:
        snapshot_file = hazard.snapshot_path.lstrip("/")
        full_path = os.path.join(os.path.dirname(settings.UPLOAD_DIR), snapshot_file)
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass

    db.delete(hazard)
    db.commit()

    # Broadcast deletion to all connected dashboards
    await ws_manager.broadcast({
        "type": "HAZARD_DELETED",
        "data": {"id": hazard_id}
    })

    return {"detail": f"Hazard #{hazard_id} deleted successfully", "id": hazard_id}


class RepairPhotoUpload(BaseModel):
    snapshot_base64: str


@router.post("/{hazard_id}/repair-photo", response_model=HazardResponse)
async def upload_repair_photo(
    hazard_id: int,
    data: RepairPhotoUpload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: upload a photo of the repaired area as proof."""
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")

    if hazard.status != "repaired":
        raise HTTPException(status_code=400, detail="Hazard must be marked as repaired first")

    repair_path = save_base64_image(data.snapshot_base64)
    if not repair_path:
        raise HTTPException(status_code=500, detail="Failed to save repair photo")

    hazard.repair_snapshot_path = repair_path
    hazard.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(hazard)

    res = format_hazard_response(hazard)
    await ws_manager.broadcast({
        "type": "HAZARD_UPDATED",
        "data": res.model_dump()
    })
    return res
