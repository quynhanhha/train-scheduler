"""
Tests for Pydantic schemas and validation logic.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.schemas import (
    StationCreate, StationUpdate, StationResponse,
    TrainCreate, TrainUpdate, TrainResponse,
    TrackSegmentCreate, TrackSegmentUpdate, TrackSegmentResponse,
    ScheduledSegmentCreate, ScheduledSegmentResponse,
    ScheduledTripCreate, ScheduledTripUpdate, ScheduledTripResponse,
    TripStatusEnum, ConflictCheckRequest, ConflictCheckResponse, ConflictDetail
)


# ============================================================================
# Station Schema Tests
# ============================================================================

def test_station_create_valid():
    """Test creating a valid station."""
    station = StationCreate(name="Central Station", num_tracks=4)
    assert station.name == "Central Station"
    assert station.num_tracks == 4


def test_station_create_default_tracks():
    """Test station creation with default track count."""
    station = StationCreate(name="Small Station")
    assert station.num_tracks == 1


def test_station_create_invalid_name():
    """Test that empty station name is rejected."""
    with pytest.raises(ValidationError):
        StationCreate(name="", num_tracks=2)


def test_station_create_invalid_track_count():
    """Test that invalid track counts are rejected."""
    # Zero tracks
    with pytest.raises(ValidationError):
        StationCreate(name="Station", num_tracks=0)
    
    # Negative tracks
    with pytest.raises(ValidationError):
        StationCreate(name="Station", num_tracks=-1)
    
    # Too many tracks
    with pytest.raises(ValidationError):
        StationCreate(name="Station", num_tracks=51)


def test_station_update_partial():
    """Test partial station update."""
    update = StationUpdate(name="New Name")
    assert update.name == "New Name"
    assert update.num_tracks is None


# ============================================================================
# Train Schema Tests
# ============================================================================

def test_train_create_valid():
    """Test creating a valid train."""
    train = TrainCreate(code="SM101", description="Express service")
    assert train.code == "SM101"
    assert train.description == "Express service"


def test_train_create_no_description():
    """Test train creation without description."""
    train = TrainCreate(code="SM102")
    assert train.code == "SM102"
    assert train.description is None


def test_train_create_invalid_code():
    """Test that empty train code is rejected."""
    with pytest.raises(ValidationError):
        TrainCreate(code="")


# ============================================================================
# Track Segment Schema Tests
# ============================================================================

def test_track_segment_create_valid():
    """Test creating a valid track segment."""
    segment = TrackSegmentCreate(
        station_a_id=1,
        station_b_id=2,
        single_track=True,
        travel_time_minutes=15
    )
    assert segment.station_a_id == 1
    assert segment.station_b_id == 2
    assert segment.single_track is True
    assert segment.travel_time_minutes == 15


def test_track_segment_same_stations():
    """Test that segment with same station for A and B is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TrackSegmentCreate(
            station_a_id=1,
            station_b_id=1,
            single_track=True,
            travel_time_minutes=15
        )
    assert "must be different" in str(exc_info.value)


def test_track_segment_invalid_time():
    """Test that invalid travel times are rejected."""
    # Zero time
    with pytest.raises(ValidationError):
        TrackSegmentCreate(
            station_a_id=1,
            station_b_id=2,
            single_track=True,
            travel_time_minutes=0
        )
    
    # Too long (more than 24 hours)
    with pytest.raises(ValidationError):
        TrackSegmentCreate(
            station_a_id=1,
            station_b_id=2,
            single_track=True,
            travel_time_minutes=1441
        )


def test_track_segment_default_single_track():
    """Test that single_track defaults to False."""
    segment = TrackSegmentCreate(
        station_a_id=1,
        station_b_id=2,
        travel_time_minutes=15
    )
    assert segment.single_track is False


# ============================================================================
# Scheduled Segment Schema Tests
# ============================================================================

def test_scheduled_segment_create_valid():
    """Test creating a valid scheduled segment."""
    departure = datetime(2025, 11, 20, 9, 0)
    arrival = datetime(2025, 11, 20, 9, 15)
    
    segment = ScheduledSegmentCreate(
        track_segment_id=1,
        departure_time=departure,
        arrival_time=arrival
    )
    assert segment.track_segment_id == 1
    assert segment.departure_time == departure
    assert segment.arrival_time == arrival


def test_scheduled_segment_arrival_before_departure():
    """Test that arrival before departure is rejected."""
    departure = datetime(2025, 11, 20, 9, 15)
    arrival = datetime(2025, 11, 20, 9, 0)
    
    with pytest.raises(ValidationError) as exc_info:
        ScheduledSegmentCreate(
            track_segment_id=1,
            departure_time=departure,
            arrival_time=arrival
        )
    assert "must be after" in str(exc_info.value)


def test_scheduled_segment_same_time():
    """Test that same departure and arrival time is rejected."""
    same_time = datetime(2025, 11, 20, 9, 0)
    
    with pytest.raises(ValidationError):
        ScheduledSegmentCreate(
            track_segment_id=1,
            departure_time=same_time,
            arrival_time=same_time
        )


# ============================================================================
# Scheduled Trip Schema Tests
# ============================================================================

def test_scheduled_trip_create_single_segment():
    """Test creating a trip with a single segment."""
    segment = ScheduledSegmentCreate(
        track_segment_id=1,
        departure_time=datetime(2025, 11, 20, 9, 0),
        arrival_time=datetime(2025, 11, 20, 9, 15)
    )
    
    trip = ScheduledTripCreate(
        train_id=1,
        segments=[segment]
    )
    assert trip.train_id == 1
    assert len(trip.segments) == 1


def test_scheduled_trip_create_multiple_segments():
    """Test creating a trip with multiple segments."""
    segments = [
        ScheduledSegmentCreate(
            track_segment_id=1,
            departure_time=datetime(2025, 11, 20, 9, 0),
            arrival_time=datetime(2025, 11, 20, 9, 15)
        ),
        ScheduledSegmentCreate(
            track_segment_id=2,
            departure_time=datetime(2025, 11, 20, 9, 15),
            arrival_time=datetime(2025, 11, 20, 9, 30)
        ),
        ScheduledSegmentCreate(
            track_segment_id=3,
            departure_time=datetime(2025, 11, 20, 9, 30),
            arrival_time=datetime(2025, 11, 20, 9, 45)
        )
    ]
    
    trip = ScheduledTripCreate(train_id=1, segments=segments)
    assert len(trip.segments) == 3


def test_scheduled_trip_no_segments():
    """Test that trip without segments is rejected."""
    with pytest.raises(ValidationError):
        ScheduledTripCreate(train_id=1, segments=[])


def test_scheduled_trip_segments_not_chronological():
    """Test that non-chronological segments are rejected."""
    segments = [
        ScheduledSegmentCreate(
            track_segment_id=1,
            departure_time=datetime(2025, 11, 20, 9, 0),
            arrival_time=datetime(2025, 11, 20, 9, 15)
        ),
        ScheduledSegmentCreate(
            track_segment_id=2,
            departure_time=datetime(2025, 11, 20, 9, 10),  # Before previous arrival!
            arrival_time=datetime(2025, 11, 20, 9, 25)
        )
    ]
    
    with pytest.raises(ValidationError) as exc_info:
        ScheduledTripCreate(train_id=1, segments=segments)
    assert "must be at or after" in str(exc_info.value)


def test_scheduled_trip_segments_with_gap():
    """Test trip with time gap between segments (allowed)."""
    segments = [
        ScheduledSegmentCreate(
            track_segment_id=1,
            departure_time=datetime(2025, 11, 20, 9, 0),
            arrival_time=datetime(2025, 11, 20, 9, 15)
        ),
        ScheduledSegmentCreate(
            track_segment_id=2,
            departure_time=datetime(2025, 11, 20, 9, 30),  # 15 min gap - station dwell time
            arrival_time=datetime(2025, 11, 20, 9, 45)
        )
    ]
    
    trip = ScheduledTripCreate(train_id=1, segments=segments)
    assert len(trip.segments) == 2


def test_trip_update_status():
    """Test updating trip status."""
    update = ScheduledTripUpdate(status=TripStatusEnum.ACTIVE)
    assert update.status == TripStatusEnum.ACTIVE


# ============================================================================
# Conflict Detection Schema Tests
# ============================================================================

def test_conflict_detail():
    """Test conflict detail schema."""
    conflict = ConflictDetail(
        track_segment_id=1,
        existing_trip_id=5,
        existing_segment_id=42,
        time_window={
            "proposed_start": "2025-11-20T09:00:00",
            "proposed_end": "2025-11-20T09:15:00",
            "existing_start": "2025-11-20T09:10:00",
            "existing_end": "2025-11-20T09:25:00"
        }
    )
    assert conflict.type == "TRACK_CONFLICT"
    assert conflict.track_segment_id == 1
    assert conflict.existing_trip_id == 5


def test_conflict_check_response_no_conflicts():
    """Test conflict check response with no conflicts."""
    response = ConflictCheckResponse(conflicts=[], has_conflicts=False)
    assert len(response.conflicts) == 0
    assert response.has_conflicts is False


def test_conflict_check_response_with_conflicts():
    """Test conflict check response with conflicts."""
    conflict = ConflictDetail(
        track_segment_id=1,
        existing_trip_id=5,
        existing_segment_id=42,
        time_window={}
    )
    response = ConflictCheckResponse(conflicts=[conflict], has_conflicts=True)
    assert len(response.conflicts) == 1
    assert response.has_conflicts is True


def test_conflict_check_request():
    """Test that ConflictCheckRequest accepts same data as ScheduledTripCreate."""
    segment = ScheduledSegmentCreate(
        track_segment_id=1,
        departure_time=datetime(2025, 11, 20, 9, 0),
        arrival_time=datetime(2025, 11, 20, 9, 15)
    )
    
    request = ConflictCheckRequest(train_id=1, segments=[segment])
    assert request.train_id == 1
    assert len(request.segments) == 1


# ============================================================================
# Response Schema Tests (with ORM mode)
# ============================================================================

def test_station_response_from_dict():
    """Test creating StationResponse from dict (simulating ORM)."""
    data = {"id": 1, "name": "Central", "num_tracks": 4}
    station = StationResponse(**data)
    assert station.id == 1
    assert station.name == "Central"


def test_train_response_from_dict():
    """Test creating TrainResponse from dict."""
    data = {"id": 1, "code": "SM101", "description": "Express"}
    train = TrainResponse(**data)
    assert train.id == 1
    assert train.code == "SM101"


def test_track_segment_response_with_stations():
    """Test TrackSegmentResponse with nested stations."""
    data = {
        "id": 1,
        "station_a_id": 1,
        "station_b_id": 2,
        "single_track": True,
        "travel_time_minutes": 15,
        "station_a": {"id": 1, "name": "Station A", "num_tracks": 2},
        "station_b": {"id": 2, "name": "Station B", "num_tracks": 3}
    }
    segment = TrackSegmentResponse(**data)
    assert segment.station_a.name == "Station A"
    assert segment.station_b.name == "Station B"


def test_trip_status_enum_values():
    """Test that trip status enum has correct values."""
    assert TripStatusEnum.PLANNED.value == "PLANNED"
    assert TripStatusEnum.ACTIVE.value == "ACTIVE"
    assert TripStatusEnum.CANCELLED.value == "CANCELLED"

