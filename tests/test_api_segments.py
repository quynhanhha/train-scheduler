"""
Tests for track segment API endpoints.
"""

import pytest

# Core fixtures (client, setup_test_database, clean_database) are automatically loaded from conftest.py


@pytest.fixture
def stations(client):
    """Create test stations."""
    station_a = client.post("/api/v1/stations", json={"name": "Station A", "num_tracks": 2})
    station_b = client.post("/api/v1/stations", json={"name": "Station B", "num_tracks": 3})
    station_c = client.post("/api/v1/stations", json={"name": "Station C", "num_tracks": 2})
    
    return {
        "a": station_a.json()["id"],
        "b": station_b.json()["id"],
        "c": station_c.json()["id"]
    }


def test_create_segment(client, stations):
    """Test creating a new track segment."""
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "single_track": True,
            "travel_time_minutes": 15
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["station_a_id"] == stations["a"]
    assert data["station_b_id"] == stations["b"]
    assert data["single_track"] is True
    assert data["travel_time_minutes"] == 15
    assert "id" in data


def test_create_segment_with_station_details(client, stations):
    """Test that created segment includes station details."""
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "single_track": False,
            "travel_time_minutes": 20
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["station_a"]["name"] == "Station A"
    assert data["station_b"]["name"] == "Station B"


def test_create_segment_default_multi_track(client, stations):
    """Test that segment defaults to multi-track."""
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "travel_time_minutes": 15
        }
    )
    assert response.status_code == 201
    assert response.json()["single_track"] is False


def test_create_segment_station_not_found(client, stations):
    """Test creating segment with non-existent station."""
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": 999,
            "station_b_id": stations["b"],
            "travel_time_minutes": 15
        }
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_segment_same_stations(client):
    """Test that segment with same station for A and B is rejected."""
    station = client.post("/api/v1/stations", json={"name": "Station", "num_tracks": 2})
    station_id = station.json()["id"]
    
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": station_id,
            "station_b_id": station_id,
            "travel_time_minutes": 15
        }
    )
    assert response.status_code == 422


def test_create_segment_duplicate(client, stations):
    """Test that duplicate segments are rejected."""
    # Create first segment
    client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "travel_time_minutes": 15
        }
    )
    
    # Try to create duplicate
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "travel_time_minutes": 20
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_segment_duplicate_bidirectional(client, stations):
    """Test that reverse duplicate segments are rejected."""
    # Create segment A -> B
    client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "travel_time_minutes": 15
        }
    )
    
    # Try to create B -> A (reverse)
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["b"],
            "station_b_id": stations["a"],
            "travel_time_minutes": 20
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_segment_invalid_time(client, stations):
    """Test that invalid travel times are rejected."""
    # Zero time
    response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "travel_time_minutes": 0
        }
    )
    assert response.status_code == 422


def test_list_segments(client, stations):
    """Test listing all segments."""
    client.post(
        "/api/v1/segments",
        json={"station_a_id": stations["a"], "station_b_id": stations["b"], "travel_time_minutes": 15}
    )
    client.post(
        "/api/v1/segments",
        json={"station_a_id": stations["b"], "station_b_id": stations["c"], "travel_time_minutes": 20}
    )
    
    response = client.get("/api/v1/segments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Check that station details are included
    assert "station_a" in data[0]
    assert "station_b" in data[0]


def test_list_segments_pagination(client, stations):
    """Test segment list pagination."""
    # Create multiple segments
    client.post(
        "/api/v1/segments",
        json={"station_a_id": stations["a"], "station_b_id": stations["b"], "travel_time_minutes": 15}
    )
    client.post(
        "/api/v1/segments",
        json={"station_a_id": stations["b"], "station_b_id": stations["c"], "travel_time_minutes": 20}
    )
    client.post(
        "/api/v1/segments",
        json={"station_a_id": stations["a"], "station_b_id": stations["c"], "travel_time_minutes": 25}
    )
    
    response = client.get("/api/v1/segments?skip=0&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_segment(client, stations):
    """Test getting a specific segment."""
    create_response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "single_track": True,
            "travel_time_minutes": 15
        }
    )
    segment_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/segments/{segment_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == segment_id
    assert data["single_track"] is True
    assert data["station_a"]["name"] == "Station A"
    assert data["station_b"]["name"] == "Station B"


def test_get_segment_not_found(client):
    """Test getting a non-existent segment."""
    response = client.get("/api/v1/segments/999")
    assert response.status_code == 404


def test_update_segment(client, stations):
    """Test updating a segment."""
    create_response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "single_track": False,
            "travel_time_minutes": 15
        }
    )
    segment_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/segments/{segment_id}",
        json={"single_track": True, "travel_time_minutes": 20}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["single_track"] is True
    assert data["travel_time_minutes"] == 20


def test_update_segment_partial(client, stations):
    """Test partial update of a segment."""
    create_response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "single_track": False,
            "travel_time_minutes": 15
        }
    )
    segment_id = create_response.json()["id"]
    
    # Update only single_track
    response = client.put(
        f"/api/v1/segments/{segment_id}",
        json={"single_track": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["single_track"] is True
    assert data["travel_time_minutes"] == 15  # Unchanged


def test_update_segment_not_found(client):
    """Test updating a non-existent segment."""
    response = client.put(
        "/api/v1/segments/999",
        json={"single_track": True}
    )
    assert response.status_code == 404


def test_delete_segment(client, stations):
    """Test deleting a segment."""
    create_response = client.post(
        "/api/v1/segments",
        json={
            "station_a_id": stations["a"],
            "station_b_id": stations["b"],
            "travel_time_minutes": 15
        }
    )
    segment_id = create_response.json()["id"]
    
    response = client.delete(f"/api/v1/segments/{segment_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/v1/segments/{segment_id}")
    assert get_response.status_code == 404


def test_delete_segment_not_found(client):
    """Test deleting a non-existent segment."""
    response = client.delete("/api/v1/segments/999")
    assert response.status_code == 404

