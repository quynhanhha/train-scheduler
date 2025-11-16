"""
Database initialization utility.

Run this script to create all database tables.
"""

from app.db import engine, Base
from app.models import Station, Train, TrackSegment, ScheduledTrip, ScheduledSegment


def init_database():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")
    print("\nTables created:")
    print("  - stations")
    print("  - trains")
    print("  - track_segments")
    print("  - scheduled_trips")
    print("  - scheduled_segments")


if __name__ == "__main__":
    init_database()

