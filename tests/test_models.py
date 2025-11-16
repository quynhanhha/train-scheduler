"""
Tests for domain models and database schema.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Station, Train, TrackSegment, ScheduledTrip, ScheduledSegment, TripStatus


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_station_creation(db_session):
    """Test creating a station."""
    station = Station(name="Central Station", num_tracks=4)
    db_session.add(station)
    db_session.commit()
    
    assert station.id is not None
    assert station.name == "Central Station"
    assert station.num_tracks == 4


def test_train_creation(db_session):
    """Test creating a train."""
    train = Train(code="SM101", description="Express service")
    db_session.add(train)
    db_session.commit()
    
    assert train.id is not None
    assert train.code == "SM101"
    assert train.description == "Express service"


def test_track_segment_with_stations(db_session):
    """Test creating a track segment between two stations."""
    station_a = Station(name="Station A", num_tracks=2)
    station_b = Station(name="Station B", num_tracks=3)
    db_session.add_all([station_a, station_b])
    db_session.commit()
    
    segment = TrackSegment(
        station_a_id=station_a.id,
        station_b_id=station_b.id,
        single_track=True,
        travel_time_minutes=15
    )
    db_session.add(segment)
    db_session.commit()
    
    assert segment.id is not None
    assert segment.single_track is True
    assert segment.travel_time_minutes == 15
    assert segment.station_a.name == "Station A"
    assert segment.station_b.name == "Station B"


def test_scheduled_trip_creation(db_session):
    """Test creating a scheduled trip."""
    train = Train(code="SM102")
    db_session.add(train)
    db_session.commit()
    
    start_time = datetime(2025, 11, 20, 9, 0)
    end_time = datetime(2025, 11, 20, 10, 0)
    
    trip = ScheduledTrip(
        train_id=train.id,
        start_time=start_time,
        end_time=end_time,
        status=TripStatus.PLANNED
    )
    db_session.add(trip)
    db_session.commit()
    
    assert trip.id is not None
    assert trip.train_id == train.id
    assert trip.status == TripStatus.PLANNED
    assert trip.start_time == start_time
    assert trip.end_time == end_time


def test_scheduled_segment_creation(db_session):
    """Test creating a scheduled segment."""
    # Create stations
    station_a = Station(name="Station A", num_tracks=2)
    station_b = Station(name="Station B", num_tracks=2)
    db_session.add_all([station_a, station_b])
    db_session.commit()
    
    # Create track segment
    track_segment = TrackSegment(
        station_a_id=station_a.id,
        station_b_id=station_b.id,
        single_track=True,
        travel_time_minutes=15
    )
    db_session.add(track_segment)
    db_session.commit()
    
    # Create train and trip
    train = Train(code="SM103")
    db_session.add(train)
    db_session.commit()
    
    trip = ScheduledTrip(
        train_id=train.id,
        start_time=datetime(2025, 11, 20, 9, 0),
        end_time=datetime(2025, 11, 20, 9, 15),
        status=TripStatus.PLANNED
    )
    db_session.add(trip)
    db_session.commit()
    
    # Create scheduled segment
    segment = ScheduledSegment(
        scheduled_trip_id=trip.id,
        track_segment_id=track_segment.id,
        departure_time=datetime(2025, 11, 20, 9, 0),
        arrival_time=datetime(2025, 11, 20, 9, 15)
    )
    db_session.add(segment)
    db_session.commit()
    
    assert segment.id is not None
    assert segment.scheduled_trip_id == trip.id
    assert segment.track_segment_id == track_segment.id
    assert segment.track_segment.single_track is True


def test_trip_with_multiple_segments(db_session):
    """Test creating a trip with multiple segments."""
    # Create stations
    stations = [
        Station(name=f"Station {i}", num_tracks=2)
        for i in range(3)
    ]
    db_session.add_all(stations)
    db_session.commit()
    
    # Create track segments
    segments = [
        TrackSegment(
            station_a_id=stations[i].id,
            station_b_id=stations[i+1].id,
            single_track=True,
            travel_time_minutes=15
        )
        for i in range(2)
    ]
    db_session.add_all(segments)
    db_session.commit()
    
    # Create train and trip
    train = Train(code="SM104")
    db_session.add(train)
    db_session.commit()
    
    trip = ScheduledTrip(
        train_id=train.id,
        start_time=datetime(2025, 11, 20, 9, 0),
        end_time=datetime(2025, 11, 20, 9, 30),
        status=TripStatus.PLANNED
    )
    db_session.add(trip)
    db_session.commit()
    
    # Create scheduled segments
    scheduled_segments = [
        ScheduledSegment(
            scheduled_trip_id=trip.id,
            track_segment_id=segments[0].id,
            departure_time=datetime(2025, 11, 20, 9, 0),
            arrival_time=datetime(2025, 11, 20, 9, 15)
        ),
        ScheduledSegment(
            scheduled_trip_id=trip.id,
            track_segment_id=segments[1].id,
            departure_time=datetime(2025, 11, 20, 9, 15),
            arrival_time=datetime(2025, 11, 20, 9, 30)
        )
    ]
    db_session.add_all(scheduled_segments)
    db_session.commit()
    
    # Verify relationships
    assert len(trip.segments) == 2
    assert trip.segments[0].track_segment.station_a.name == "Station 0"
    assert trip.segments[1].track_segment.station_b.name == "Station 2"


def test_trip_status_enum(db_session):
    """Test that trip status enum works correctly."""
    train = Train(code="SM105")
    db_session.add(train)
    db_session.commit()
    
    trip = ScheduledTrip(
        train_id=train.id,
        start_time=datetime(2025, 11, 20, 9, 0),
        end_time=datetime(2025, 11, 20, 10, 0),
        status=TripStatus.PLANNED
    )
    db_session.add(trip)
    db_session.commit()
    
    # Change status
    trip.status = TripStatus.ACTIVE
    db_session.commit()
    
    # Verify
    db_session.refresh(trip)
    assert trip.status == TripStatus.ACTIVE
    
    # Cancel
    trip.status = TripStatus.CANCELLED
    db_session.commit()
    db_session.refresh(trip)
    assert trip.status == TripStatus.CANCELLED


def test_cascade_delete_trip_segments(db_session):
    """Test that deleting a trip cascades to its segments."""
    # Setup
    station_a = Station(name="Station A", num_tracks=2)
    station_b = Station(name="Station B", num_tracks=2)
    db_session.add_all([station_a, station_b])
    db_session.commit()
    
    track_segment = TrackSegment(
        station_a_id=station_a.id,
        station_b_id=station_b.id,
        single_track=True,
        travel_time_minutes=15
    )
    db_session.add(track_segment)
    db_session.commit()
    
    train = Train(code="SM106")
    db_session.add(train)
    db_session.commit()
    
    trip = ScheduledTrip(
        train_id=train.id,
        start_time=datetime(2025, 11, 20, 9, 0),
        end_time=datetime(2025, 11, 20, 9, 15),
        status=TripStatus.PLANNED
    )
    db_session.add(trip)
    db_session.commit()
    
    segment = ScheduledSegment(
        scheduled_trip_id=trip.id,
        track_segment_id=track_segment.id,
        departure_time=datetime(2025, 11, 20, 9, 0),
        arrival_time=datetime(2025, 11, 20, 9, 15)
    )
    db_session.add(segment)
    db_session.commit()
    
    segment_id = segment.id
    
    # Delete the trip
    db_session.delete(trip)
    db_session.commit()
    
    # Verify segment was also deleted
    deleted_segment = db_session.query(ScheduledSegment).filter_by(id=segment_id).first()
    assert deleted_segment is None

