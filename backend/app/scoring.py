import math
from typing import Tuple, List
from sqlalchemy.orm import Session
from backend.app.models import Hazard

CLASS_BASE_WEIGHTS = {
    "pothole": 50.0,
    "crack": 30.0,
    "animal": 40.0,
}

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def find_nearby_cluster(
    db: Session,
    lat: float,
    lon: float,
    hazard_class: str,
    radius_meters: float = 15.0
) -> Tuple[int, List[int]]:
    """
    Find existing hazards of the same class within radius_meters.
    Returns (cluster_count, list_of_matching_hazard_ids).
    """
    # Fetch active hazards (not marked repaired)
    hazards = db.query(Hazard).filter(
        Hazard.hazard_class == hazard_class,
        Hazard.status != "repaired"
    ).all()

    matching_ids = []
    for h in hazards:
        dist = haversine_distance_meters(lat, lon, h.latitude, h.longitude)
        if dist <= radius_meters:
            matching_ids.append(h.id)

    return len(matching_ids) + 1, matching_ids

def calculate_severity_score(
    hazard_class: str,
    confidence: float,
    cluster_count: int = 1
) -> float:
    """
    Calculates severity score (0 to 100) based on:
    - Base class weight (pothole=50, crack=30, animal=40)
    - Detection confidence factor (up to 25 points)
    - Spatial cluster/repeat count (up to 25 points for repeated sightings)
    """
    base = CLASS_BASE_WEIGHTS.get(hazard_class.lower(), 35.0)
    confidence_pts = min(25.0, max(0.0, confidence * 25.0))
    repeat_pts = min(25.0, max(0.0, (cluster_count - 1) * 8.0))

    total = base + confidence_pts + repeat_pts
    return round(min(100.0, max(0.0, total)), 2)
