"""
Scheduling service for trip management.

Handles trip creation, validation, and conflict detection.
"""

from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import List, Dict, Any

from app.models import Train, TrackSegment, ScheduledTrip, ScheduledSegment, TripStatus
from app.schemas import ScheduledTripCreate


class SchedulingError(Exception):
    """Base exception for scheduling errors."""
    pass


class ValidationError(SchedulingError):
    """Raised when trip validation fails."""
    pass


class ConflictError(SchedulingError):
    """Raised when scheduling conflicts are detected."""
    
    def __init__(self, conflicts: List[Dict[str, Any]]):
        self.conflicts = conflicts
        super().__init__(f"Scheduling conflicts detected: {len(conflicts)} conflict(s)")


def find_conflicts(
    db: Session, 
    trip_data: ScheduledTripCreate,
    exclude_trip_id: int = None
) -> List[Dict[str, Any]]:
    """
    Check for time-based conflicts on single-track segments.
    
    A conflict occurs when:
    1. The track segment is single-track (num_tracks == 1)
    2. Another PLANNED or ACTIVE trip uses the same segment
    3. The time windows overlap
    
    Two time ranges [start1, end1] and [start2, end2] overlap if:
        start1 < end2 AND start2 < end1
    
    Args:
        db: Database session
        trip_data: Trip data to check for conflicts
        exclude_trip_id: Optional trip ID to exclude (for updates)
        
    Returns:
        List of conflict dictionaries with details about each conflict
    """
    conflicts = []
    
    # Get track segment details
    segment_ids = [seg.track_segment_id for seg in trip_data.segments]
    track_segments = db.query(TrackSegment).options(
        joinedload(TrackSegment.station_a),
        joinedload(TrackSegment.station_b)
    ).filter(
        TrackSegment.id.in_(segment_ids)
    ).all()
    track_segment_map = {ts.id: ts for ts in track_segments}
    
    for new_segment in trip_data.segments:
        track_segment = track_segment_map.get(new_segment.track_segment_id)
        
        # Skip if track segment not found (will be caught by validation)
        if not track_segment:
            continue
            
        # Only check conflicts on single-track segments
        if not track_segment.single_track:
            continue
        
        # Query for existing scheduled segments on this track
        existing_segments = db.query(ScheduledSegment).join(
            ScheduledTrip
        ).options(
            joinedload(ScheduledSegment.trip)
        ).filter(
            ScheduledSegment.track_segment_id == new_segment.track_segment_id,
            ScheduledTrip.status.in_([TripStatus.PLANNED, TripStatus.ACTIVE])
        ).all()
        
        # Exclude segments from the trip being updated (if applicable)
        if exclude_trip_id:
            existing_segments = [
                seg for seg in existing_segments 
                if seg.scheduled_trip_id != exclude_trip_id
            ]
        
        # Check for time overlaps
        for existing_segment in existing_segments:
            # Two time ranges overlap if: start1 < end2 AND start2 < end1
            if (new_segment.departure_time < existing_segment.arrival_time and
                existing_segment.departure_time < new_segment.arrival_time):
                
                conflicts.append({
                    "track_segment_id": track_segment.id,
                    "track_segment_name": f"{track_segment.station_a.name} - {track_segment.station_b.name}",
                    "conflicting_trip_id": existing_segment.scheduled_trip_id,
                    "conflicting_train_id": existing_segment.trip.train_id,
                    "new_departure": new_segment.departure_time.isoformat(),
                    "new_arrival": new_segment.arrival_time.isoformat(),
                    "existing_departure": existing_segment.departure_time.isoformat(),
                    "existing_arrival": existing_segment.arrival_time.isoformat(),
                })
    
    return conflicts


def create_trip(db: Session, trip_data: ScheduledTripCreate) -> ScheduledTrip:
    """
    Create a new scheduled trip with its segments.
    
    Validates:
    - Train exists
    - All track segments exist
    - Times are valid (departure < arrival for each segment)
    - Segments are chronologically ordered
    - No conflicts on single-track segments
    
    Args:
        db: Database session
        trip_data: Trip creation data with segments
        
    Returns:
        Created ScheduledTrip with segments
        
    Raises:
        ValidationError: If validation fails
        ConflictError: If scheduling conflicts are detected
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
    
    # Check for scheduling conflicts on single-track segments
    conflicts = find_conflicts(db, trip_data)
    if conflicts:
        raise ConflictError(conflicts)
    
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

