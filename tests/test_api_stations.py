"""
Tests for station API endpoints.
"""

# Fixtures are automatically loaded from conftest.py


def test_create_station(client):
    """Test creating a new station."""
    response = client.post(
        "/api/v1/stations",
        json={"name": "Central Station", "num_tracks": 4}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Central Station"
    assert data["num_tracks"] == 4
    assert "id" in data


def test_create_station_duplicate_name(client):
    """Test that creating a station with duplicate name fails."""
    client.post("/api/v1/stations", json={"name": "Central", "num_tracks": 2})
    
    response = client.post("/api/v1/stations", json={"name": "Central", "num_tracks": 3})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_station_default_tracks(client):
    """Test station creation with default track count."""
    response = client.post("/api/v1/stations", json={"name": "Small Station"})
    assert response.status_code == 201
    assert response.json()["num_tracks"] == 1


def test_create_station_invalid_data(client):
    """Test that invalid station data is rejected."""
    # Empty name
    response = client.post("/api/v1/stations", json={"name": "", "num_tracks": 2})
    assert response.status_code == 422
    
    # Invalid track count
    response = client.post("/api/v1/stations", json={"name": "Station", "num_tracks": 0})
    assert response.status_code == 422


def test_list_stations(client):
    """Test listing all stations."""
    # Create some stations
    client.post("/api/v1/stations", json={"name": "Station A", "num_tracks": 2})
    client.post("/api/v1/stations", json={"name": "Station B", "num_tracks": 3})
    client.post("/api/v1/stations", json={"name": "Station C", "num_tracks": 1})
    
    response = client.get("/api/v1/stations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "Station A"


def test_list_stations_pagination(client):
    """Test station list pagination."""
    # Create stations
    for i in range(5):
        client.post("/api/v1/stations", json={"name": f"Station {i}", "num_tracks": 2})
    
    # Get first 3
    response = client.get("/api/v1/stations?skip=0&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    # Get next 2
    response = client.get("/api/v1/stations?skip=3&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_station(client):
    """Test getting a specific station."""
    create_response = client.post(
        "/api/v1/stations",
        json={"name": "Test Station", "num_tracks": 5}
    )
    station_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/stations/{station_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == station_id
    assert data["name"] == "Test Station"
    assert data["num_tracks"] == 5


def test_get_station_not_found(client):
    """Test getting a non-existent station."""
    response = client.get("/api/v1/stations/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_station(client):
    """Test updating a station."""
    create_response = client.post(
        "/api/v1/stations",
        json={"name": "Old Name", "num_tracks": 2}
    )
    station_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/stations/{station_id}",
        json={"name": "New Name", "num_tracks": 4}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["num_tracks"] == 4


def test_update_station_partial(client):
    """Test partial update of a station."""
    create_response = client.post(
        "/api/v1/stations",
        json={"name": "Station", "num_tracks": 2}
    )
    station_id = create_response.json()["id"]
    
    # Update only name
    response = client.put(
        f"/api/v1/stations/{station_id}",
        json={"name": "Updated Station"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Station"
    assert data["num_tracks"] == 2  # Unchanged


def test_update_station_duplicate_name(client):
    """Test that updating to a duplicate name fails."""
    client.post("/api/v1/stations", json={"name": "Station A", "num_tracks": 2})
    create_response = client.post("/api/v1/stations", json={"name": "Station B", "num_tracks": 3})
    station_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/stations/{station_id}",
        json={"name": "Station A"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_update_station_not_found(client):
    """Test updating a non-existent station."""
    response = client.put(
        "/api/v1/stations/999",
        json={"name": "New Name"}
    )
    assert response.status_code == 404


def test_delete_station(client):
    """Test deleting a station."""
    create_response = client.post(
        "/api/v1/stations",
        json={"name": "To Delete", "num_tracks": 2}
    )
    station_id = create_response.json()["id"]
    
    response = client.delete(f"/api/v1/stations/{station_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/v1/stations/{station_id}")
    assert get_response.status_code == 404


def test_delete_station_with_segments(client):
    """Test that deleting a station with track segments fails."""
    # Create stations and segment
    station_a_response = client.post("/api/v1/stations", json={"name": "Station A", "num_tracks": 2})
    station_b_response = client.post("/api/v1/stations", json={"name": "Station B", "num_tracks": 2})
    
    station_a_id = station_a_response.json()["id"]
    station_b_id = station_b_response.json()["id"]
    
    client.post(
        "/api/v1/segments",
        json={
            "station_a_id": station_a_id,
            "station_b_id": station_b_id,
            "single_track": True,
            "travel_time_minutes": 15
        }
    )
    
    # Try to delete station A
    response = client.delete(f"/api/v1/stations/{station_a_id}")
    assert response.status_code == 400
    assert "referenced by track segments" in response.json()["detail"]


def test_delete_station_not_found(client):
    """Test deleting a non-existent station."""
    response = client.delete("/api/v1/stations/999")
    assert response.status_code == 404

