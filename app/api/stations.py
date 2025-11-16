"""
API endpoints for station management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.models import Station
from app.schemas import StationCreate, StationUpdate, StationResponse


router = APIRouter(prefix="/stations", tags=["Stations"])


@router.post("", response_model=StationResponse, status_code=status.HTTP_201_CREATED)
def create_station(station: StationCreate, db: Session = Depends(get_db)):
    """Create a new station."""
    # Check if station name already exists
    existing = db.query(Station).filter(Station.name == station.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Station with name '{station.name}' already exists"
        )
    
    db_station = Station(**station.model_dump())
    db.add(db_station)
    db.commit()
    db.refresh(db_station)
    return db_station


@router.get("", response_model=List[StationResponse])
def list_stations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all stations with pagination."""
    stations = db.query(Station).offset(skip).limit(limit).all()
    return stations


@router.get("/{station_id}", response_model=StationResponse)
def get_station(station_id: int, db: Session = Depends(get_db)):
    """Get a specific station by ID."""
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with id {station_id} not found"
        )
    return station


@router.put("/{station_id}", response_model=StationResponse)
def update_station(
    station_id: int, 
    station_update: StationUpdate, 
    db: Session = Depends(get_db)
):
    """Update a station."""
    db_station = db.query(Station).filter(Station.id == station_id).first()
    if not db_station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with id {station_id} not found"
        )
    
    # Check for name conflict if name is being updated
    if station_update.name and station_update.name != db_station.name:
        existing = db.query(Station).filter(Station.name == station_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Station with name '{station_update.name}' already exists"
            )
    
    # Update fields
    update_data = station_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_station, field, value)
    
    db.commit()
    db.refresh(db_station)
    return db_station


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_station(station_id: int, db: Session = Depends(get_db)):
    """Delete a station."""
    db_station = db.query(Station).filter(Station.id == station_id).first()
    if not db_station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with id {station_id} not found"
        )
    
    # Check if station is referenced by track segments
    if db_station.segments_as_a or db_station.segments_as_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete station that is referenced by track segments"
        )
    
    db.delete(db_station)
    db.commit()
    return None

