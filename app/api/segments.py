"""
API endpoints for track segment management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.db import get_db
from app.models import TrackSegment, Station
from app.schemas import TrackSegmentCreate, TrackSegmentUpdate, TrackSegmentResponse


router = APIRouter(prefix="/segments", tags=["Track Segments"])


@router.post("", response_model=TrackSegmentResponse, status_code=status.HTTP_201_CREATED)
def create_segment(segment: TrackSegmentCreate, db: Session = Depends(get_db)):
    """Create a new track segment."""
    # Verify stations exist
    station_a = db.query(Station).filter(Station.id == segment.station_a_id).first()
    if not station_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with id {segment.station_a_id} not found"
        )
    
    station_b = db.query(Station).filter(Station.id == segment.station_b_id).first()
    if not station_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with id {segment.station_b_id} not found"
        )
    
    # Check for duplicate segment (bidirectional)
    existing = db.query(TrackSegment).filter(
        (
            (TrackSegment.station_a_id == segment.station_a_id) &
            (TrackSegment.station_b_id == segment.station_b_id)
        ) | (
            (TrackSegment.station_a_id == segment.station_b_id) &
            (TrackSegment.station_b_id == segment.station_a_id)
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Track segment between stations {segment.station_a_id} and {segment.station_b_id} already exists"
        )
    
    db_segment = TrackSegment(**segment.model_dump())
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    
    # Load relationships for response
    db.refresh(db_segment)
    return db_segment


@router.get("", response_model=List[TrackSegmentResponse])
def list_segments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all track segments with pagination."""
    segments = db.query(TrackSegment).options(
        joinedload(TrackSegment.station_a),
        joinedload(TrackSegment.station_b)
    ).offset(skip).limit(limit).all()
    return segments


@router.get("/{segment_id}", response_model=TrackSegmentResponse)
def get_segment(segment_id: int, db: Session = Depends(get_db)):
    """Get a specific track segment by ID."""
    segment = db.query(TrackSegment).options(
        joinedload(TrackSegment.station_a),
        joinedload(TrackSegment.station_b)
    ).filter(TrackSegment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track segment with id {segment_id} not found"
        )
    return segment


@router.put("/{segment_id}", response_model=TrackSegmentResponse)
def update_segment(
    segment_id: int,
    segment_update: TrackSegmentUpdate,
    db: Session = Depends(get_db)
):
    """Update a track segment."""
    db_segment = db.query(TrackSegment).filter(TrackSegment.id == segment_id).first()
    if not db_segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track segment with id {segment_id} not found"
        )
    
    # Update fields
    update_data = segment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_segment, field, value)
    
    db.commit()
    db.refresh(db_segment)
    
    # Load relationships for response
    db.refresh(db_segment)
    return db_segment


@router.delete("/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_segment(segment_id: int, db: Session = Depends(get_db)):
    """Delete a track segment."""
    db_segment = db.query(TrackSegment).filter(TrackSegment.id == segment_id).first()
    if not db_segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track segment with id {segment_id} not found"
        )
    
    # Check if segment is referenced by scheduled segments
    if db_segment.scheduled_segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete track segment that is referenced by scheduled trips"
        )
    
    db.delete(db_segment)
    db.commit()
    return None

