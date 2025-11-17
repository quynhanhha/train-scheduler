"""
Tests for conflict detection on single-track segments.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

from app.main import app
from app.db import Base, get_db
from app import models

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_conflicts.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables once
Base.metadata.create_all(bind=engine)


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
    if os.path.exists("./test_conflicts.db"):
        os.remove("./test_conflicts.db")


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
def setup_basic_data(client):
    """Setup basic stations, trains, and track segments."""
    # Create stations
    station_a = client.post("/api/v1/stations", json={"name": "Station A", "num_tracks": 1})
    station_b = client.post("/api/v1/stations", json={"name": "Station B", "num_tracks": 1})
    station_c = client.post("/api/v1/stations", json={"name": "Station C", "num_tracks": 1})
    
    assert station_a.status_code == 201, f"Station A creation failed: {station_a.json()}"
    assert station_b.status_code == 201, f"Station B creation failed: {station_b.json()}"
    assert station_c.status_code == 201, f"Station C creation failed: {station_c.json()}"
    
    station_a_id = station_a.json()["id"]
    station_b_id = station_b.json()["id"]
    station_c_id = station_c.json()["id"]
    
    # Create trains
    train1 = client.post("/api/v1/trains", json={"code": "EXP101", "description": "Express 101"})
    train2 = client.post("/api/v1/trains", json={"code": "LOC202", "description": "Local 202"})
    
    assert train1.status_code == 201, f"Train 1 creation failed: {train1.json()}"
    assert train2.status_code == 201, f"Train 2 creation failed: {train2.json()}"
    
    train1_id = train1.json()["id"]
    train2_id = train2.json()["id"]
    
    # Create single-track segments
    segment_ab = client.post("/api/v1/segments", json={
        "station_a_id": station_a_id,
        "station_b_id": station_b_id,
        "distance_km": 50,
        "travel_time_minutes": 30,
        "single_track": True  # Single track
    })
    
    assert segment_ab.status_code == 201, f"Segment AB creation failed: {segment_ab.status_code} - {segment_ab.json()}"
    
    segment_bc = client.post("/api/v1/segments", json={
        "station_a_id": station_b_id,
        "station_b_id": station_c_id,
        "distance_km": 60,
        "travel_time_minutes": 40,
        "single_track": False  # Double track - no conflicts
    })
    
    assert segment_bc.status_code == 201, f"Segment BC creation failed: {segment_bc.status_code} - {segment_bc.json()}"
    
    segment_ab_id = segment_ab.json()["id"]
    segment_bc_id = segment_bc.json()["id"]
    
    return {
        "station_a_id": station_a_id,
        "station_b_id": station_b_id,
        "station_c_id": station_c_id,
        "train1_id": train1_id,
        "train2_id": train2_id,
        "segment_ab_id": segment_ab_id,  # single track
        "segment_bc_id": segment_bc_id,  # double track
    }


def test_no_conflict_on_empty_schedule(client, setup_basic_data):
    """First trip on a track should have no conflicts."""
    data = setup_basic_data
    
    trip_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response = client.post("/api/v1/trips", json=trip_data)
    assert response.status_code == 201
    assert "id" in response.json()


def test_conflict_on_exact_time_overlap(client, setup_basic_data):
    """Two trips with exact same times should conflict."""
    data = setup_basic_data
    
    # Create first trip
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    
    # Try to create second trip with exact same times
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 409
    assert "conflicts" in response2.json()["detail"]
    conflicts = response2.json()["detail"]["conflicts"]
    assert len(conflicts) == 1
    assert conflicts[0]["track_segment_id"] == data["segment_ab_id"]


def test_conflict_on_partial_overlap(client, setup_basic_data):
    """Trips with partial time overlap should conflict."""
    data = setup_basic_data
    
    # Create first trip: 10:00 - 11:00
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    
    # Try to create second trip: 10:30 - 11:30 (overlaps from 10:30 - 11:00)
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:30:00",
                "arrival_time": "2025-01-01T11:30:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 409
    assert "conflicts" in response2.json()["detail"]


def test_no_conflict_on_sequential_trips(client, setup_basic_data):
    """Sequential trips with no overlap should not conflict."""
    data = setup_basic_data
    
    # Create first trip: 10:00 - 11:00
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    
    # Create second trip: 11:00 - 12:00 (starts exactly when first ends)
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T11:00:00",
                "arrival_time": "2025-01-01T12:00:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 201


def test_no_conflict_on_double_track(client, setup_basic_data):
    """Multiple trips on double-track segment should not conflict."""
    data = setup_basic_data
    
    # Create first trip on double-track segment
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_bc_id"],  # double track
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    
    # Create second trip with same times on double-track
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_bc_id"],  # double track
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 201  # Should succeed - no conflict on double track


def test_conflict_only_on_single_track_segment(client, setup_basic_data):
    """Trip with multiple segments should only conflict on single-track segment."""
    data = setup_basic_data
    
    # Create first trip: A->B (single track) then B->C (double track)
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],  # single track
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            },
            {
                "track_segment_id": data["segment_bc_id"],  # double track
                "departure_time": "2025-01-01T11:00:00",
                "arrival_time": "2025-01-01T12:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    
    # Try to create second trip with same times on both segments
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],  # single track - will conflict
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            },
            {
                "track_segment_id": data["segment_bc_id"],  # double track - no conflict
                "departure_time": "2025-01-01T11:00:00",
                "arrival_time": "2025-01-01T12:00:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 409
    conflicts = response2.json()["detail"]["conflicts"]
    assert len(conflicts) == 1  # Only one conflict
    assert conflicts[0]["track_segment_id"] == data["segment_ab_id"]  # On single track


def test_no_conflict_with_cancelled_trip(client, setup_basic_data):
    """Cancelled trips should not cause conflicts."""
    data = setup_basic_data
    
    # Create first trip
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    trip1_id = response1.json()["id"]
    
    # Cancel the first trip
    cancel_response = client.put(
        f"/api/v1/trips/{trip1_id}",
        json={"status": "CANCELLED"}
    )
    assert cancel_response.status_code == 200
    
    # Create second trip with same times - should succeed since first is cancelled
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 201


def test_conflict_with_active_trip(client, setup_basic_data):
    """Active trips should cause conflicts."""
    data = setup_basic_data
    
    # Create first trip
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    trip1_id = response1.json()["id"]
    
    # Set first trip to ACTIVE
    activate_response = client.put(
        f"/api/v1/trips/{trip1_id}",
        json={"status": "ACTIVE"}
    )
    assert activate_response.status_code == 200
    
    # Try to create second trip with overlapping times
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:30:00",
                "arrival_time": "2025-01-01T11:30:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 409


def test_multiple_conflicts_detected(client, setup_basic_data):
    """Should detect all conflicts when multiple segments overlap."""
    data = setup_basic_data
    
    # Create a station D and another single-track segment
    station_d = client.post("/api/v1/stations", json={"name": "Station D", "num_tracks": 1})
    station_d_id = station_d.json()["id"]
    
    segment_cd = client.post("/api/v1/segments", json={
        "station_a_id": data["station_c_id"],
        "station_b_id": station_d_id,
        "distance_km": 40,
        "travel_time_minutes": 25,
        "single_track": True  # Single track
    })
    segment_cd_id = segment_cd.json()["id"]
    
    # Create first trip on multiple segments
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            },
            {
                "track_segment_id": data["segment_bc_id"],
                "departure_time": "2025-01-01T11:00:00",
                "arrival_time": "2025-01-01T12:00:00"
            },
            {
                "track_segment_id": segment_cd_id,
                "departure_time": "2025-01-01T12:00:00",
                "arrival_time": "2025-01-01T13:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    
    # Try to create trip that overlaps on multiple single-track segments
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:30:00",
                "arrival_time": "2025-01-01T11:30:00"
            },
            {
                "track_segment_id": data["segment_bc_id"],
                "departure_time": "2025-01-01T11:30:00",
                "arrival_time": "2025-01-01T12:30:00"
            },
            {
                "track_segment_id": segment_cd_id,
                "departure_time": "2025-01-01T12:30:00",
                "arrival_time": "2025-01-01T13:30:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 409
    conflicts = response2.json()["detail"]["conflicts"]
    # Should have 2 conflicts (segment_ab and segment_cd), but not segment_bc (double track)
    assert len(conflicts) == 2
    conflict_segment_ids = [c["track_segment_id"] for c in conflicts]
    assert data["segment_ab_id"] in conflict_segment_ids
    assert segment_cd_id in conflict_segment_ids
    assert data["segment_bc_id"] not in conflict_segment_ids  # Double track - no conflict


def test_conflict_details_structure(client, setup_basic_data):
    """Verify conflict response contains all required details."""
    data = setup_basic_data
    
    # Create first trip
    trip1_data = {
        "train_id": data["train1_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:00:00",
                "arrival_time": "2025-01-01T11:00:00"
            }
        ]
    }
    
    response1 = client.post("/api/v1/trips", json=trip1_data)
    assert response1.status_code == 201
    trip1_id = response1.json()["id"]
    
    # Try to create conflicting trip
    trip2_data = {
        "train_id": data["train2_id"],
        "segments": [
            {
                "track_segment_id": data["segment_ab_id"],
                "departure_time": "2025-01-01T10:30:00",
                "arrival_time": "2025-01-01T11:30:00"
            }
        ]
    }
    
    response2 = client.post("/api/v1/trips", json=trip2_data)
    assert response2.status_code == 409
    
    detail = response2.json()["detail"]
    assert "message" in detail
    assert "conflicts" in detail
    
    conflict = detail["conflicts"][0]
    assert "track_segment_id" in conflict
    assert "track_segment_name" in conflict
    assert "conflicting_trip_id" in conflict
    assert conflict["conflicting_trip_id"] == trip1_id
    assert "conflicting_train_id" in conflict
    assert conflict["conflicting_train_id"] == data["train1_id"]
    assert "new_departure" in conflict
    assert "new_arrival" in conflict
    assert "existing_departure" in conflict
    assert "existing_arrival" in conflict

