"""
Scheduling service for trip management.

Handles trip creation, validation, and (later) conflict detection.
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.models import Train, TrackSegment, ScheduledTrip, ScheduledSegment, TripStatus
from app.schemas import ScheduledTripCreate


class SchedulingError(Exception):
    """Base exception for scheduling errors."""
    pass


class ValidationError(SchedulingError):
    """Raised when trip validation fails."""
    pass


def create_trip(db: Session, trip_data: ScheduledTripCreate) -> ScheduledTrip:
    """
    Create a new scheduled trip with its segments.
    
    Validates:
    - Train exists
    - All track segments exist
    - Times are valid (departure < arrival for each segment)
    - Segments are chronologically ordered
    
    Args:
        db: Database session
        trip_data: Trip creation data with segments
        
    Returns:
        Created ScheduledTrip with segments
        
    Raises:
        ValidationError: If validation fails
    """
    # Validate train exists
    train = db.query(Train).filter(Train.id == trip_data.train_id).first()
    if not train:
        raise ValidationError(f"Train with id {trip_data.train_id} not found")
    
    # Validate all track segments exist
    segment_ids = [seg.track_segment_id for seg in trip_data.segments]
    track_segments = db.query(TrackSegment).filter(
        TrackSegment.id.in_(segment_ids)
    ).all()
    
    found_ids = {ts.id for ts in track_segments}
    missing_ids = set(segment_ids) - found_ids
    if missing_ids:
        raise ValidationError(f"Track segments not found: {sorted(missing_ids)}")
    
    # Validate times for each segment (departure < arrival)
    for i, segment in enumerate(trip_data.segments):
        if segment.departure_time >= segment.arrival_time:
            raise ValidationError(
                f"Segment {i}: departure_time must be before arrival_time"
            )
    
    # Validate chronological ordering across segments
    for i in range(len(trip_data.segments) - 1):
        current = trip_data.segments[i]
        next_seg = trip_data.segments[i + 1]
        
        if next_seg.departure_time < current.arrival_time:
            raise ValidationError(
                f"Segment {i+1} departure ({next_seg.departure_time}) must be "
                f"at or after segment {i} arrival ({current.arrival_time})"
            )
    
    # Compute overall trip start and end times
    start_time = trip_data.segments[0].departure_time
    end_time = trip_data.segments[-1].arrival_time
    
    # Create the trip
    db_trip = ScheduledTrip(
        train_id=trip_data.train_id,
        start_time=start_time,
        end_time=end_time,
        status=TripStatus.PLANNED
    )
    db.add(db_trip)
    db.flush()  # Get the trip ID without committing
    
    # Create the segments
    for segment_data in trip_data.segments:
        db_segment = ScheduledSegment(
            scheduled_trip_id=db_trip.id,
            track_segment_id=segment_data.track_segment_id,
            departure_time=segment_data.departure_time,
            arrival_time=segment_data.arrival_time
        )
        db.add(db_segment)
    
    db.commit()
    db.refresh(db_trip)
    
    return db_trip


def get_trip(db: Session, trip_id: int) -> ScheduledTrip:
    """Get a trip by ID."""
    trip = db.query(ScheduledTrip).filter(ScheduledTrip.id == trip_id).first()
    if not trip:
        raise ValidationError(f"Trip with id {trip_id} not found")
    return trip


def list_trips(db: Session, skip: int = 0, limit: int = 100) -> List[ScheduledTrip]:
    """List all trips with pagination."""
    return db.query(ScheduledTrip).offset(skip).limit(limit).all()


def update_trip_status(
    db: Session, 
    trip_id: int, 
    status: TripStatus
) -> ScheduledTrip:
    """Update a trip's status."""
    trip = get_trip(db, trip_id)
    trip.status = status
    db.commit()
    db.refresh(trip)
    return trip


def delete_trip(db: Session, trip_id: int) -> None:
    """Delete a trip (and its segments via cascade)."""
    trip = get_trip(db, trip_id)
    db.delete(trip)
    db.commit()

