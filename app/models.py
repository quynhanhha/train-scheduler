"""
SQLAlchemy ORM models for the train scheduler application.

Domain Model:
- Station: Physical stations with track capacity
- Train: Rolling stock/vehicles
- TrackSegment: Connection between two stations (can be single-track)
- ScheduledTrip: A single run of a train
- ScheduledSegment: Individual leg of a trip on a track segment
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db import Base


class TripStatus(enum.Enum):
    """Status of a scheduled trip."""
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class Station(Base):
    """
    Represents a physical railway station.
    
    Attributes:
        id: Primary key
        name: Station name (must be unique)
        num_tracks: Number of tracks available at this station
    """
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    num_tracks = Column(Integer, nullable=False, default=1)

    # Relationships
    segments_as_a = relationship(
        "TrackSegment",
        foreign_keys="TrackSegment.station_a_id",
        back_populates="station_a"
    )
    segments_as_b = relationship(
        "TrackSegment",
        foreign_keys="TrackSegment.station_b_id",
        back_populates="station_b"
    )

    def __repr__(self):
        return f"<Station(id={self.id}, name='{self.name}', tracks={self.num_tracks})>"


class Train(Base):
    """
    Represents a train (rolling stock/vehicle).
    
    Attributes:
        id: Primary key
        code: Unique train identifier (e.g., "SM101")
        description: Optional description
    """
    __tablename__ = "trains"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)

    # Relationships
    scheduled_trips = relationship("ScheduledTrip", back_populates="train")

    def __repr__(self):
        return f"<Train(id={self.id}, code='{self.code}')>"


class TrackSegment(Base):
    """
    Represents a track segment connecting two stations.
    
    This is the core resource for conflict detection.
    Single-track segments can only be occupied by one train at a time.
    
    Attributes:
        id: Primary key
        station_a_id: Foreign key to first station
        station_b_id: Foreign key to second station
        single_track: Whether this is a single-track segment (conflict-prone)
        travel_time_minutes: Expected travel time between stations
    """
    __tablename__ = "track_segments"

    id = Column(Integer, primary_key=True, index=True)
    station_a_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    station_b_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    single_track = Column(Boolean, default=False, nullable=False)
    travel_time_minutes = Column(Integer, nullable=False)

    # Relationships
    station_a = relationship("Station", foreign_keys=[station_a_id], back_populates="segments_as_a")
    station_b = relationship("Station", foreign_keys=[station_b_id], back_populates="segments_as_b")
    scheduled_segments = relationship("ScheduledSegment", back_populates="track_segment")

    def __repr__(self):
        track_type = "single" if self.single_track else "multi"
        return f"<TrackSegment(id={self.id}, {self.station_a_id}↔{self.station_b_id}, {track_type}-track, {self.travel_time_minutes}min)>"


class ScheduledTrip(Base):
    """
    Represents a scheduled run of a train.
    
    A trip consists of multiple segments and has an overall time window.
    
    Attributes:
        id: Primary key
        train_id: Foreign key to the train
        start_time: Overall trip start time
        end_time: Overall trip end time
        status: Current status (PLANNED, ACTIVE, CANCELLED)
    """
    __tablename__ = "scheduled_trips"

    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.id"), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    status = Column(SQLEnum(TripStatus), default=TripStatus.PLANNED, nullable=False, index=True)

    # Relationships
    train = relationship("Train", back_populates="scheduled_trips")
    segments = relationship("ScheduledSegment", back_populates="trip", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScheduledTrip(id={self.id}, train_id={self.train_id}, status={self.status.value}, {self.start_time} → {self.end_time})>"


class ScheduledSegment(Base):
    """
    Represents one leg of a scheduled trip.
    
    This is where conflict detection happens: two segments using the same
    single-track segment with overlapping times create a conflict.
    
    Attributes:
        id: Primary key
        scheduled_trip_id: Foreign key to the parent trip
        track_segment_id: Foreign key to the track segment being used
        departure_time: When the train departs this segment
        arrival_time: When the train arrives at the end of this segment
    """
    __tablename__ = "scheduled_segments"

    id = Column(Integer, primary_key=True, index=True)
    scheduled_trip_id = Column(Integer, ForeignKey("scheduled_trips.id"), nullable=False)
    track_segment_id = Column(Integer, ForeignKey("track_segments.id"), nullable=False, index=True)
    departure_time = Column(DateTime, nullable=False, index=True)
    arrival_time = Column(DateTime, nullable=False, index=True)

    # Relationships
    trip = relationship("ScheduledTrip", back_populates="segments")
    track_segment = relationship("TrackSegment", back_populates="scheduled_segments")

    def __repr__(self):
        return f"<ScheduledSegment(id={self.id}, trip_id={self.scheduled_trip_id}, segment_id={self.track_segment_id}, {self.departure_time} → {self.arrival_time})>"

