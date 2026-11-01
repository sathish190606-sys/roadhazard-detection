import pytest
from backend.app.scoring import haversine_distance_meters, calculate_severity_score

def test_haversine_distance_same_point():
    dist = haversine_distance_meters(12.9716, 77.5946, 12.9716, 77.5946)
    assert dist == 0.0

def test_haversine_distance_known_points():
    # Approx 111 km per degree of latitude
    dist = haversine_distance_meters(0.0, 0.0, 1.0, 0.0)
    assert 110000 < dist < 112000

def test_calculate_severity_score_pothole():
    # Pothole base = 50. Confidence 0.8 => 50 + 20 = 70. Cluster 1 => 0 repeat pts.
    score = calculate_severity_score("pothole", 0.8, cluster_count=1)
    assert score == 70.0

def test_calculate_severity_score_crack():
    # Crack base = 30. Confidence 0.5 => 30 + 12.5 = 42.5.
    score = calculate_severity_score("crack", 0.5, cluster_count=1)
    assert score == 42.5

def test_calculate_severity_score_animal():
    # Animal base = 40. Confidence 1.0 => 40 + 25 = 65.
    score = calculate_severity_score("animal", 1.0, cluster_count=1)
    assert score == 65.0

def test_calculate_severity_score_clustering():
    # Repeat sightings should increase score up to max 100
    base_score = calculate_severity_score("pothole", 0.9, cluster_count=1)
    clustered_score = calculate_severity_score("pothole", 0.9, cluster_count=4)
    assert clustered_score > base_score
    assert clustered_score <= 100.0
