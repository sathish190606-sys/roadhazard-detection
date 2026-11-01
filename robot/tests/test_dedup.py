import time
import pytest
from robot.detector import Deduplicator, haversine_distance

def test_haversine_distance():
    # 0 meters for same coordinate
    assert haversine_distance(12.9716, 77.5946, 12.9716, 77.5946) == 0.0
    # Small offset: ~1.1 meters (0.00001 deg lat ~ 1.11m)
    dist = haversine_distance(12.9716, 77.5946, 12.97161, 77.5946)
    assert 1.0 < dist < 1.3

def test_dedup_spatial_filtering():
    dedup = Deduplicator(distance_threshold_m=5.0, time_window_sec=10.0)
    now = time.time()

    # First sighting -> Not duplicate
    assert dedup.is_duplicate("pothole", 12.971600, 77.594600, now) is False

    # Second sighting ~1.1 meters away, 1 second later -> Duplicate!
    assert dedup.is_duplicate("pothole", 12.971610, 77.594600, now + 1.0) is True

    # Different class at same coordinate -> Not duplicate!
    assert dedup.is_duplicate("crack", 12.971600, 77.594600, now + 2.0) is False

    # Sighting 20 meters away -> Not duplicate!
    assert dedup.is_duplicate("pothole", 12.971800, 77.594600, now + 2.0) is False

def test_dedup_temporal_expiration():
    dedup = Deduplicator(distance_threshold_m=5.0, time_window_sec=5.0)
    now = time.time()

    assert dedup.is_duplicate("pothole", 12.971600, 77.594600, now) is False
    # Within 5s window -> Duplicate
    assert dedup.is_duplicate("pothole", 12.971600, 77.594600, now + 3.0) is True
    # After 5s window expired (e.g. 8s later) -> New valid detection
    assert dedup.is_duplicate("pothole", 12.971600, 77.594600, now + 8.0) is False
