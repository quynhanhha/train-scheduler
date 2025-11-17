"""
API endpoints for trip management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.db import get_db
from app.models import ScheduledTrip, ScheduledSegment, TrackSegment
from app.schemas import (
    ScheduledTripCreate,
    ScheduledTripUpdate,
    ScheduledTripResponse
)
from app.services.scheduling_service import (
    create_trip,
    get_trip,
    list_trips,
    update_trip_status,
    delete_trip,
    ValidationError
)


router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("", response_model=ScheduledTripResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_trip(trip: ScheduledTripCreate, db: Session = Depends(get_db)):
    """
    Create a new scheduled trip.
    
    A trip consists of:
    - A train
    - One or more segments (track segments with departure/arrival times)
    
    Validates:
    - Train exists
    - All track segments exist
    - Times are valid and chronologically ordered
    """
    try:
        db_trip = create_trip(db, trip)
        
        # Load relationships for response
        db.refresh(db_trip)
        return db_trip
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[ScheduledTripResponse])
def list_scheduled_trips(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all scheduled trips with pagination."""
    trips = list_trips(db, skip, limit)
    return trips


@router.get("/{trip_id}", response_model=ScheduledTripResponse)
def get_scheduled_trip(trip_id: int, db: Session = Depends(get_db)):
    """Get a specific trip by ID."""
    try:
        trip = get_trip(db, trip_id)
        return trip
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{trip_id}/segments", response_model=ScheduledTripResponse)
def get_trip_segments(trip_id: int, db: Session = Depends(get_db)):
    """Get a trip with its segments."""
    try:
        trip = db.query(ScheduledTrip).options(
            joinedload(ScheduledTrip.segments).joinedload(ScheduledSegment.track_segment)
        ).filter(ScheduledTrip.id == trip_id).first()
        
        if not trip:
            raise ValidationError(f"Trip with id {trip_id} not found")
        
        return trip
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/{trip_id}", response_model=ScheduledTripResponse)
def update_scheduled_trip(
    trip_id: int,
    trip_update: ScheduledTripUpdate,
    db: Session = Depends(get_db)
):
    """Update a trip (currently only status updates)."""
    try:
        if trip_update.status is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        from app.models import TripStatus
        # Convert string enum to TripStatus enum
        status_enum = TripStatus[trip_update.status.value]
        
        db_trip = update_trip_status(db, trip_id, status_enum)
        return db_trip
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_trip(trip_id: int, db: Session = Depends(get_db)):
    """Delete a trip (and its segments)."""
    try:
        delete_trip(db, trip_id)
        return None
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

