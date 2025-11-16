"""
Pydantic schemas for request/response validation.

Schema Pattern:
- Base: Shared fields
- Create: Fields required for creation
- Update: Fields for updates (optional)
- Response: Complete object with ID (from_attributes=True for ORM)
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class TripStatusEnum(str, Enum):
    """Trip status values for API."""
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


# ============================================================================
# Station Schemas
# ============================================================================

class StationBase(BaseModel):
    """Base station schema with shared fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Station name")
    num_tracks: int = Field(default=1, ge=1, le=50, description="Number of tracks at station")


class StationCreate(StationBase):
    """Schema for creating a new station."""
    pass


class StationUpdate(BaseModel):
    """Schema for updating a station."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    num_tracks: Optional[int] = Field(None, ge=1, le=50)


class StationResponse(StationBase):
    """Schema for station responses."""
    id: int

    model_config = {"from_attributes": True}


# ============================================================================
# Train Schemas
# ============================================================================

class TrainBase(BaseModel):
    """Base train schema with shared fields."""
    code: str = Field(..., min_length=1, max_length=50, description="Unique train code (e.g., SM101)")
    description: Optional[str] = Field(None, max_length=500, description="Optional train description")


class TrainCreate(TrainBase):
    """Schema for creating a new train."""
    pass


class TrainUpdate(BaseModel):
    """Schema for updating a train."""
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)


class TrainResponse(TrainBase):
    """Schema for train responses."""
    id: int

    model_config = {"from_attributes": True}


# ============================================================================
# Track Segment Schemas
# ============================================================================

class TrackSegmentBase(BaseModel):
    """Base track segment schema with shared fields."""
    station_a_id: int = Field(..., gt=0, description="ID of first station")
    station_b_id: int = Field(..., gt=0, description="ID of second station")
    single_track: bool = Field(default=False, description="Whether this is a single-track segment")
    travel_time_minutes: int = Field(..., gt=0, le=1440, description="Travel time in minutes")

    @field_validator('station_b_id')
    @classmethod
    def stations_must_differ(cls, v, info):
        """Ensure station_a and station_b are different."""
        if 'station_a_id' in info.data and v == info.data['station_a_id']:
            raise ValueError('station_a_id and station_b_id must be different')
        return v


class TrackSegmentCreate(TrackSegmentBase):
    """Schema for creating a new track segment."""
    pass


class TrackSegmentUpdate(BaseModel):
    """Schema for updating a track segment."""
    single_track: Optional[bool] = None
    travel_time_minutes: Optional[int] = Field(None, gt=0, le=1440)


class TrackSegmentResponse(TrackSegmentBase):
    """Schema for track segment responses."""
    id: int
    station_a: Optional[StationResponse] = None
    station_b: Optional[StationResponse] = None

    model_config = {"from_attributes": True}


# ============================================================================
# Scheduled Segment Schemas (for trips)
# ============================================================================

class ScheduledSegmentBase(BaseModel):
    """Base scheduled segment schema."""
    track_segment_id: int = Field(..., gt=0, description="ID of track segment")
    departure_time: datetime = Field(..., description="Departure time")
    arrival_time: datetime = Field(..., description="Arrival time")

    @field_validator('arrival_time')
    @classmethod
    def arrival_after_departure(cls, v, info):
        """Ensure arrival time is after departure time."""
        if 'departure_time' in info.data and v <= info.data['departure_time']:
            raise ValueError('arrival_time must be after departure_time')
        return v


class ScheduledSegmentCreate(ScheduledSegmentBase):
    """Schema for creating a scheduled segment (used in trip creation)."""
    pass


class ScheduledSegmentResponse(ScheduledSegmentBase):
    """Schema for scheduled segment responses."""
    id: int
    scheduled_trip_id: int
    track_segment: Optional[TrackSegmentResponse] = None

    model_config = {"from_attributes": True}


# ============================================================================
# Scheduled Trip Schemas
# ============================================================================

class ScheduledTripBase(BaseModel):
    """Base scheduled trip schema."""
    train_id: int = Field(..., gt=0, description="ID of the train")


class ScheduledTripCreate(ScheduledTripBase):
    """
    Schema for creating a new scheduled trip.
    
    Includes nested segments that define the route.
    Times are validated to ensure they're increasing.
    """
    segments: List[ScheduledSegmentCreate] = Field(
        ..., 
        min_length=1,
        description="List of segments that make up this trip"
    )

    @field_validator('segments')
    @classmethod
    def validate_segment_times(cls, segments):
        """Ensure segment times are chronologically ordered."""
        if len(segments) < 1:
            raise ValueError('Trip must have at least one segment')
        
        for i in range(len(segments) - 1):
            current_arrival = segments[i].arrival_time
            next_departure = segments[i + 1].departure_time
            
            # Next segment should depart at or after current arrival
            if next_departure < current_arrival:
                raise ValueError(
                    f'Segment {i+1} departure time must be at or after segment {i} arrival time'
                )
        
        return segments


class ScheduledTripUpdate(BaseModel):
    """Schema for updating a trip (mainly status changes)."""
    status: Optional[TripStatusEnum] = None


class ScheduledTripResponse(ScheduledTripBase):
    """Schema for scheduled trip responses."""
    id: int
    start_time: datetime
    end_time: datetime
    status: TripStatusEnum
    train: Optional[TrainResponse] = None
    segments: List[ScheduledSegmentResponse] = []

    model_config = {"from_attributes": True}


# ============================================================================
# Conflict Detection Schemas
# ============================================================================

class ConflictDetail(BaseModel):
    """Details about a single track conflict."""
    type: str = Field(default="TRACK_CONFLICT", description="Type of conflict")
    track_segment_id: int = Field(..., description="ID of conflicting track segment")
    existing_trip_id: int = Field(..., description="ID of existing conflicting trip")
    existing_segment_id: int = Field(..., description="ID of existing conflicting segment")
    time_window: dict = Field(..., description="Time window details showing overlap")


class ConflictCheckRequest(ScheduledTripCreate):
    """
    Schema for checking conflicts without creating a trip.
    Identical to ScheduledTripCreate but used for planning endpoint.
    """
    pass


class ConflictCheckResponse(BaseModel):
    """Response from conflict check."""
    conflicts: List[ConflictDetail] = Field(
        default_factory=list,
        description="List of conflicts found (empty if none)"
    )
    has_conflicts: bool = Field(..., description="Whether any conflicts were found")


class TripCreationResponse(BaseModel):
    """Response when trip creation fails due to conflicts."""
    message: str
    conflicts: List[ConflictDetail]


# ============================================================================
# Health Check Schema
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str

