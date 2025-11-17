# Train Scheduler API

A railway scheduling system with time-based conflict detection on single-track segments. Built with FastAPI, SQLAlchemy, and SQLite.

## Overview

This system manages train scheduling across a railway network, ensuring safe operations by detecting and preventing conflicts when multiple trains attempt to use single-track segments simultaneously. The core feature is **time-based conflict detection**: when scheduling a trip, the system checks if any segment of the route is a single-track section that overlaps in time with another planned or active trip. If a conflict is detected, the system returns detailed information about the conflicting trips, enabling operators to adjust schedules before committing changes.

---

## Domain Model

The system models five core entities:

### **Station**
A location where trains stop. Stations are connected by track segments.
- **Attributes**: name, num_tracks (platform capacity)
- **Relationships**: Connected to other stations via track segments

### **TrackSegment**
A physical rail connection between two stations.
- **Attributes**: travel_time_minutes, **single_track** (boolean)
- **Relationships**: Connects station_a ↔ station_b
- **Conflict Rule**: If `single_track=True`, only one train can use it at any given time

### **Train**
A physical train that can be assigned to trips.
- **Attributes**: code (unique identifier), description
- **Relationships**: Can have multiple scheduled trips

### **ScheduledTrip**
A planned journey for a specific train across one or more track segments.
- **Attributes**: train_id, start_time, end_time, status (PLANNED/ACTIVE/CANCELLED)
- **Relationships**: Composed of multiple ScheduledSegments

### **ScheduledSegment**
One leg of a trip, representing a train's use of a specific track segment with departure/arrival times.
- **Attributes**: departure_time, arrival_time
- **Relationships**: Belongs to a ScheduledTrip, uses a TrackSegment
- **Validation**: departure_time < arrival_time, segments must be chronologically ordered

### Entity Relationship Diagram

```
                          ┌─────────┐
                          │ Station │ (PK: id)
                          └─────────┘
                            ▲     ▲
                            │ 1   │ 1
                            │     │
         station_a_id (FK)  │     │ station_b_id (FK)
                            │     │ 
                            │ N   │ N
                      ┌──────────────┐
                      │ TrackSegment │ (PK: id)
                      └──────────────┘
                            ▲
                            │ 1
      track_segment_id (FK) │
                            │
                            │ N
                    ┌──────────────────┐
                    │ ScheduledSegment │ (PK: id)
                    └──────────────────┘
                            │ N
                            │ scheduled_trip_id (FK)
                            │
                            ▼ 1
                      ┌──────────────┐
                      │ScheduledTrip │ (PK: id)
                      └──────────────┘
                            │ N
                            │ train_id (FK)
                            │
                            ▼ 1
                        ┌───────┐
                        │ Train │ (PK: id)
                        └───────┘
```
---

## Conflict Detection

### Single-Track Constraint

Railway operations require exclusive use of single-track segments. When `TrackSegment.single_track = True`, only one train can occupy that segment at any given moment. Multi-track segments (`single_track = False`) allow concurrent usage.

### Time Overlap Algorithm

Two time ranges **[start₁, end₁]** and **[start₂, end₂]** overlap if and only if:

```
start₁ < end₂  AND  start₂ < end₁
```

**Example scenarios:**

| Scenario | Trip A | Trip B | Conflict? |
|----------|--------|--------|-----------|
| Sequential | 10:00-11:00 | 11:00-12:00 | No (boundary touch is allowed) |
| Partial overlap | 10:00-11:00 | 10:30-11:30 | Yes |
| Full containment | 10:00-12:00 | 10:30-11:00 | Yes |
| Separate | 10:00-11:00 | 12:00-13:00 | No |

### Conflict Detection Process

1. **Input**: Proposed trip with segments and times
2. **Filter**: Check only single-track segments (`single_track = True`)
3. **Query**: Find existing trips with status PLANNED or ACTIVE for the same `track_segment_id` where time windows overlap
4. **Compare**: Apply time overlap formula for each pair
5. **Output**: 
   - **No conflicts** → HTTP 201 Created
   - **Conflicts found** → HTTP 409 Conflict with detailed conflict report

### Conflict Response Format

```json
{
  "message": "Scheduling conflicts detected: 1 conflict(s)",
  "conflicts": [
    {
      "track_segment_id": 1,
      "track_segment_name": "Station A - Station B",
      "conflicting_trip_id": 5,
      "conflicting_train_id": 2,
      "new_departure": "2025-01-01T10:30:00",
      "new_arrival": "2025-01-01T11:30:00",
      "existing_departure": "2025-01-01T10:00:00",
      "existing_arrival": "2025-01-01T11:00:00"
    }
  ]
}
```

---

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────────────┐
│                   API Layer                         │
│  (app/api/)                                         │
│  - FastAPI routers                                  │
│  - Request/response handling                        │
│  - HTTP status codes                                │
│  - Input validation (Pydantic)                      │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                 Service Layer                       │
│  (app/services/)                                    │
│  - Business logic                                   │
│  - Conflict detection algorithm                     │
│  - Trip validation                                  │
│  - Error handling (ValidationError, ConflictError)  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                 Database Layer                      │
│  (app/models.py, app/db.py)                         │
│  - SQLAlchemy ORM models                            │
│  - Database session management                      │
│  - Relationships & foreign keys                     │
└─────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Service Layer Isolation**: Conflict detection logic lives in `scheduling_service.py`, not in the API layer. This separation allows:
   - Reusability across multiple endpoints
   - Easier unit testing
   - Business logic changes without touching HTTP layer
   - Keeping conflict detection in the service layer makes it easy to reuse in both `/trips` and `/trips/conflicts/check` without duplicating logic

2. **Exception-Based Flow Control**: Uses custom exceptions (`ValidationError`, `ConflictError`) that the API layer translates to appropriate HTTP responses (400, 409).

3. **Read-Only Validation Endpoint**: `/trips/conflicts/check` allows operators to simulate trip creation without database writes—critical for planning workflows.

---

## Project Structure

```
train-scheduler/
├── app/
│   ├── main.py              # FastAPI application & lifespan events
│   ├── db.py                # SQLAlchemy engine & session management
│   ├── models.py            # ORM models (Station, Train, etc.)
│   ├── schemas.py           # Pydantic schemas for validation
│   ├── api/                 # API endpoints
│   │   ├── stations.py      # Station CRUD
│   │   ├── trains.py        # Train CRUD
│   │   ├── segments.py      # TrackSegment CRUD
│   │   └── trips.py         # Trip creation & conflict checking
│   └── services/
│       └── scheduling_service.py  # Conflict detection logic
├── tests/
│   ├── conftest.py          # Shared test fixtures
│   ├── test_models.py       # Model tests
│   ├── test_schemas.py      # Schema validation tests
│   ├── test_api_*.py        # API endpoint tests
│   └── test_conflicts.py    # Conflict detection unit tests
├── requirements.txt         # Python dependencies
├── run.sh                   # Application startup script
├── run_tests.sh             # Test runner script
└── README.md                # This file
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd "train scheduler"
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   # Option 1: Using startup script
   ./run.sh

   # Option 2: Using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application**
   - **API Base URL**: http://localhost:8000
   - **Interactive Docs (Swagger)**: http://localhost:8000/docs
   - **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
   - **Health Check**: http://localhost:8000/health

---

## API Usage Examples

### Using HTTPie

```bash
# Create stations
http POST :8000/api/v1/stations name="Southern Cross" num_tracks=16
http POST :8000/api/v1/stations name="Flinders Street" num_tracks=12

# Create a train
http POST :8000/api/v1/trains code="MT01" description="Metro Train - Comeng Set"

# Create a single-track segment
http POST :8000/api/v1/segments \
  station_a_id=1 \
  station_b_id=2 \
  travel_time_minutes=180 \
  single_track:=true

# Schedule a trip
http POST :8000/api/v1/trips \
  train_id=1 \
  segments:='[
    {
      "track_segment_id": 1,
      "departure_time": "2025-01-15T10:00:00",
      "arrival_time": "2025-01-15T13:00:00"
    }
  ]'

# Check for conflicts (read-only validation)
http POST :8000/api/v1/trips/conflicts/check \
  train_id=1 \
  segments:='[
    {
      "track_segment_id": 1,
      "departure_time": "2025-01-15T11:00:00",
      "arrival_time": "2025-01-15T14:00:00"
    }
  ]'
# Returns 409 if conflict detected
```

### Using cURL

```bash
# Create a station
curl -X POST http://localhost:8000/api/v1/stations \
  -H "Content-Type: application/json" \
  -d '{"name": "Southern Cross", "num_tracks": 16}'

# Create a trip
curl -X POST http://localhost:8000/api/v1/trips \
  -H "Content-Type: application/json" \
  -d '{
    "train_id": 1,
    "segments": [
      {
        "track_segment_id": 1,
        "departure_time": "2025-01-15T10:00:00",
        "arrival_time": "2025-01-15T13:00:00"
      }
    ]
  }'

# Check conflicts
curl -X POST http://localhost:8000/api/v1/trips/conflicts/check \
  -H "Content-Type: application/json" \
  -d '{
    "train_id": 2,
    "segments": [
      {
        "track_segment_id": 1,
        "departure_time": "2025-01-15T11:00:00",
        "arrival_time": "2025-01-15T14:00:00"
      }
    ]
  }'
```

---

## Testing

### Run All Tests

```bash
# Using test runner script (recommended)
./run_tests.sh

# Or using pytest directly
pytest -v
```

### Test Coverage

```bash
pytest --cov=app --cov-report=html tests/
# Opens htmlcov/index.html for detailed coverage report
```

### Test Suite Breakdown

| Test Suite | Tests | Focus |
|------------|-------|-------|
| `test_models.py` | 8 | ORM model creation & relationships |
| `test_schemas.py` | 28 | Pydantic validation logic |
| `test_main.py` | 1 | Health check endpoint |
| `test_api_stations.py` | 15 | Station CRUD operations |
| `test_api_trains.py` | 15 | Train CRUD operations |
| `test_api_segments.py` | 17 | Track segment CRUD |
| `test_api_trips.py` | 24 | Trip creation & conflict checks |
| `test_conflicts.py` | 10 | Conflict detection algorithm |
| **TOTAL** | **118** | **Comprehensive coverage** |

---

## API Reference

### Endpoints

#### **Stations**
- `POST /api/v1/stations` - Create station
- `GET /api/v1/stations` - List all stations
- `GET /api/v1/stations/{id}` - Get station by ID
- `PUT /api/v1/stations/{id}` - Update station
- `DELETE /api/v1/stations/{id}` - Delete station

#### **Trains**
- `POST /api/v1/trains` - Create train
- `GET /api/v1/trains` - List all trains
- `GET /api/v1/trains/{id}` - Get train by ID
- `PUT /api/v1/trains/{id}` - Update train
- `DELETE /api/v1/trains/{id}` - Delete train

#### **Track Segments**
- `POST /api/v1/segments` - Create track segment
- `GET /api/v1/segments` - List all segments
- `GET /api/v1/segments/{id}` - Get segment by ID
- `PUT /api/v1/segments/{id}` - Update segment
- `DELETE /api/v1/segments/{id}` - Delete segment

#### **Scheduled Trips**
- `POST /api/v1/trips` - Create scheduled trip (with conflict detection)
- `POST /api/v1/trips/conflicts/check` - Validate trip without creating (read-only)
- `GET /api/v1/trips` - List all trips
- `GET /api/v1/trips/{id}` - Get trip by ID
- `GET /api/v1/trips/{id}/segments` - Get trip with detailed segments
- `PUT /api/v1/trips/{id}` - Update trip status
- `DELETE /api/v1/trips/{id}` - Delete trip

### Response Codes

| Code | Meaning | Usage |
|------|---------|-------|
| **200** | OK | Successful GET/PUT operations |
| **201** | Created | Resource successfully created |
| **204** | No Content | Successful DELETE |
| **400** | Bad Request | Validation error (invalid data) |
| **404** | Not Found | Resource doesn't exist |
| **409** | Conflict | Scheduling conflict detected |
| **422** | Unprocessable Entity | Schema validation failed |

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI 0.109+ | Async API with auto-documentation |
| **Database** | SQLite | File-based SQL database |
| **ORM** | SQLAlchemy 2.0+ | Database abstraction & relationships |
| **Validation** | Pydantic 2.0+ | Request/response schema validation |
| **ASGI Server** | Uvicorn | High-performance async server |
| **Testing** | Pytest | Test framework with fixtures |
| **HTTP Client** | HTTPX | TestClient dependency |

---

## Future Extensions

### 1. **Multi-Track Capacity Management**
Currently, tracks are binary (single/multi). Enhancement:
- Add `capacity: int` to TrackSegment
- Track concurrent usage count
- Reject when `active_trains >= capacity`

**Use case**: Double-track segments can handle 2 trains simultaneously.

### 2. **Dynamic Rescheduling & Delay Propagation**
When a trip is delayed:
- Automatically detect downstream conflicts
- Suggest alternative schedules
- Propagate delays to connected trips

**Algorithm**: Graph traversal through connected segments + time adjustment.

### 3. **Train Priority Classes**
Introduce priority levels (e.g., passenger > freight):
- Higher priority trains get scheduling preference
- Lower priority trains are suggested for rescheduling when conflicts occur

**Schema change**: Add `priority: int` to Train model.

### 4. **Real-Time GPS Tracking Integration**
- Update trip status (PLANNED → ACTIVE → COMPLETED) based on GPS data
- Detect early arrivals / delays in real-time
- Trigger conflict re-checks on delay events

### 5. **Historical Analytics & Optimization**
- Track on-time performance by train/route
- Identify chronically congested segments
- ML-based schedule optimization suggestions

### 6. **Authentication & Multi-Tenant Support**
- JWT-based authentication
- Role-based access control (dispatcher, viewer, admin)
- Separate schedules per railway operator

### 7. **WebSocket for Real-Time Updates**
- Push conflict alerts to connected clients
- Live trip status updates
- Real-time schedule board

---

## Author

**Quynh Anh Ha**  
