"""
API endpoints for train management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.models import Train
from app.schemas import TrainCreate, TrainUpdate, TrainResponse


router = APIRouter(prefix="/trains", tags=["Trains"])


@router.post("", response_model=TrainResponse, status_code=status.HTTP_201_CREATED)
def create_train(train: TrainCreate, db: Session = Depends(get_db)):
    """Create a new train."""
    # Check if train code already exists
    existing = db.query(Train).filter(Train.code == train.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Train with code '{train.code}' already exists"
        )
    
    db_train = Train(**train.model_dump())
    db.add(db_train)
    db.commit()
    db.refresh(db_train)
    return db_train


@router.get("", response_model=List[TrainResponse])
def list_trains(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all trains with pagination."""
    trains = db.query(Train).offset(skip).limit(limit).all()
    return trains


@router.get("/{train_id}", response_model=TrainResponse)
def get_train(train_id: int, db: Session = Depends(get_db)):
    """Get a specific train by ID."""
    train = db.query(Train).filter(Train.id == train_id).first()
    if not train:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Train with id {train_id} not found"
        )
    return train


@router.put("/{train_id}", response_model=TrainResponse)
def update_train(
    train_id: int, 
    train_update: TrainUpdate, 
    db: Session = Depends(get_db)
):
    """Update a train."""
    db_train = db.query(Train).filter(Train.id == train_id).first()
    if not db_train:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Train with id {train_id} not found"
        )
    
    # Check for code conflict if code is being updated
    if train_update.code and train_update.code != db_train.code:
        existing = db.query(Train).filter(Train.code == train_update.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Train with code '{train_update.code}' already exists"
            )
    
    # Update fields
    update_data = train_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_train, field, value)
    
    db.commit()
    db.refresh(db_train)
    return db_train


@router.delete("/{train_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_train(train_id: int, db: Session = Depends(get_db)):
    """Delete a train."""
    db_train = db.query(Train).filter(Train.id == train_id).first()
    if not db_train:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Train with id {train_id} not found"
        )
    
    # Check if train has scheduled trips
    if db_train.scheduled_trips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete train that has scheduled trips"
        )
    
    db.delete(db_train)
    db.commit()
    return None

