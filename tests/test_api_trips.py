"""
Tests for trip API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app import models


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_trips.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    """Create tables once for all tests in this module."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up test database file
    import os
    if os.path.exists("./test_trips.db"):
        os.remove("./test_trips.db")


@pytest.fixture(autouse=True)
def clean_database():
    """Clean all tables before each test."""
    session = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
    yield


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def test_data(client):
    """Create basic test data: stations, track segments, and a train."""
    # Create stations
    station_a = client.post("/api/v1/stations", json={"name": "Station A", "num_tracks": 2})
    station_b = client.post("/api/v1/stations", json={"name": "Station B", "num_tracks": 2})
    station_c = client.post("/api/v1/stations", json={"name": "Station C", "num_tracks": 2})
    
    # Create track segments
    segment_ab = client.post("/api/v1/segments", json={
        "station_a_id": station_a.json()["id"],
        "station_b_id": station_b.json()["id"],
        "single_track": True,
        "travel_time_minutes": 15
    })
    segment_bc = client.post("/api/v1/segments", json={
        "station_a_id": station_b.json()["id"],
        "station_b_id": station_c.json()["id"],
        "single_track": False,
        "travel_time_minutes": 20
    })
    
    # Create train
    train = client.post("/api/v1/trains", json={"code": "SM101", "description": "Express"})
    
    return {
        "stations": {
            "a": station_a.json()["id"],
            "b": station_b.json()["id"],
            "c": station_c.json()["id"]
        },
        "segments": {
            "ab": segment_ab.json()["id"],
            "bc": segment_bc.json()["id"]
        },
        "train": train.json()["id"]
    }


def test_create_trip_single_segment(client, test_data):
    """Test creating a trip with a single segment."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            }
        ]
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["train_id"] == test_data["train"]
    assert data["status"] == "PLANNED"
    assert len(data["segments"]) == 1
    assert "id" in data


def test_create_trip_multiple_segments(client, test_data):
    """Test creating a trip with multiple segments."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            },
            {
                "track_segment_id": test_data["segments"]["bc"],
                "departure_time": (base_time + timedelta(minutes=15)).isoformat(),
                "arrival_time": (base_time + timedelta(minutes=35)).isoformat()
            }
        ]
    })
    
    assert response.status_code == 201
    data = response.json()
    assert len(data["segments"]) == 2
    assert data["start_time"] == base_time.isoformat()
    assert data["end_time"] == (base_time + timedelta(minutes=35)).isoformat()


def test_create_trip_with_dwell_time(client, test_data):
    """Test creating a trip with gap between segments (station dwell time)."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            },
            {
                "track_segment_id": test_data["segments"]["bc"],
                "departure_time": (base_time + timedelta(minutes=25)).isoformat(),  # 10 min dwell
                "arrival_time": (base_time + timedelta(minutes=45)).isoformat()
            }
        ]
    })
    
    assert response.status_code == 201


def test_create_trip_train_not_found(client, test_data):
    """Test that creating a trip with non-existent train fails."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    response = client.post("/api/v1/trips", json={
        "train_id": 999,
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            }
        ]
    })
    
    assert response.status_code == 400
    assert "Train" in response.json()["detail"]
    assert "not found" in response.json()["detail"]


def test_create_trip_segment_not_found(client, test_data):
    """Test that creating a trip with non-existent track segment fails."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": 999,
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            }
        ]
    })
    
    assert response.status_code == 400
    assert "Track segments not found" in response.json()["detail"]


def test_create_trip_invalid_segment_times(client, test_data):
    """Test that segment with arrival before departure is rejected."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time - timedelta(minutes=5)).isoformat()  # Before departure!
            }
        ]
    })
    
    assert response.status_code == 422  # Pydantic validation


def test_create_trip_non_chronological_segments(client, test_data):
    """Test that non-chronological segments are rejected."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            },
            {
                "track_segment_id": test_data["segments"]["bc"],
                "departure_time": (base_time + timedelta(minutes=10)).isoformat(),  # Before previous arrival!
                "arrival_time": (base_time + timedelta(minutes=30)).isoformat()
            }
        ]
    })
    
    assert response.status_code == 422  # Pydantic validation


def test_create_trip_no_segments(client, test_data):
    """Test that trip without segments is rejected."""
    response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": []
    })
    
    assert response.status_code == 422


def test_list_trips(client, test_data):
    """Test listing all trips."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    # Create multiple trips
    for i in range(3):
        client.post("/api/v1/trips", json={
            "train_id": test_data["train"],
            "segments": [
                {
                    "track_segment_id": test_data["segments"]["ab"],
                    "departure_time": (base_time + timedelta(hours=i)).isoformat(),
                    "arrival_time": (base_time + timedelta(hours=i, minutes=15)).isoformat()
                }
            ]
        })
    
    response = client.get("/api/v1/trips")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_list_trips_pagination(client, test_data):
    """Test trip list pagination."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    # Create 5 trips
    for i in range(5):
        client.post("/api/v1/trips", json={
            "train_id": test_data["train"],
            "segments": [
                {
                    "track_segment_id": test_data["segments"]["ab"],
                    "departure_time": (base_time + timedelta(hours=i)).isoformat(),
                    "arrival_time": (base_time + timedelta(hours=i, minutes=15)).isoformat()
                }
            ]
        })
    
    # Get first 3
    response = client.get("/api/v1/trips?skip=0&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3
    
    # Get next 2
    response = client.get("/api/v1/trips?skip=3&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_trip(client, test_data):
    """Test getting a specific trip."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    create_response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            }
        ]
    })
    trip_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/trips/{trip_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trip_id
    assert data["train_id"] == test_data["train"]


def test_get_trip_not_found(client):
    """Test getting a non-existent trip."""
    response = client.get("/api/v1/trips/999")
    assert response.status_code == 404


def test_get_trip_segments(client, test_data):
    """Test getting a trip with its segments."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    create_response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            },
            {
                "track_segment_id": test_data["segments"]["bc"],
                "departure_time": (base_time + timedelta(minutes=15)).isoformat(),
                "arrival_time": (base_time + timedelta(minutes=35)).isoformat()
            }
        ]
    })
    trip_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/trips/{trip_id}/segments")
    assert response.status_code == 200
    data = response.json()
    assert len(data["segments"]) == 2


def test_update_trip_status(client, test_data):
    """Test updating a trip's status."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    create_response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            }
        ]
    })
    trip_id = create_response.json()["id"]
    
    # Update to ACTIVE
    response = client.put(f"/api/v1/trips/{trip_id}", json={"status": "ACTIVE"})
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    
    # Update to CANCELLED
    response = client.put(f"/api/v1/trips/{trip_id}", json={"status": "CANCELLED"})
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_update_trip_not_found(client):
    """Test updating a non-existent trip."""
    response = client.put("/api/v1/trips/999", json={"status": "ACTIVE"})
    assert response.status_code == 404


def test_delete_trip(client, test_data):
    """Test deleting a trip."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    create_response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            }
        ]
    })
    trip_id = create_response.json()["id"]
    
    # Delete the trip
    response = client.delete(f"/api/v1/trips/{trip_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/v1/trips/{trip_id}")
    assert get_response.status_code == 404


def test_delete_trip_not_found(client):
    """Test deleting a non-existent trip."""
    response = client.delete("/api/v1/trips/999")
    assert response.status_code == 404


def test_delete_trip_cascades_to_segments(client, test_data):
    """Test that deleting a trip also deletes its segments."""
    base_time = datetime(2025, 11, 20, 9, 0)
    
    create_response = client.post("/api/v1/trips", json={
        "train_id": test_data["train"],
        "segments": [
            {
                "track_segment_id": test_data["segments"]["ab"],
                "departure_time": base_time.isoformat(),
                "arrival_time": (base_time + timedelta(minutes=15)).isoformat()
            },
            {
                "track_segment_id": test_data["segments"]["bc"],
                "departure_time": (base_time + timedelta(minutes=15)).isoformat(),
                "arrival_time": (base_time + timedelta(minutes=35)).isoformat()
            }
        ]
    })
    trip_id = create_response.json()["id"]
    
    # Delete the trip
    client.delete(f"/api/v1/trips/{trip_id}")
    
    # Try to get segments - trip should not exist
    response = client.get(f"/api/v1/trips/{trip_id}/segments")
    assert response.status_code == 404

