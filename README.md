# Train Scheduler

A FastAPI-based train scheduling application.

## Project Structure

```
train-scheduler/
├── app/
│   ├── main.py          # FastAPI application entry point
│   ├── db.py            # Database configuration
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic schemas
│   ├── api/             # API route handlers
│   │   └── __init__.py
│   └── services/        # Business logic
│       └── __init__.py
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   # Option 1: Using the startup script
   ./run.sh
   
   # Option 2: Using uvicorn directly
   uvicorn app.main:app --reload
   ```
   
   **Important:** Always run from the project root directory (`train scheduler/`), not from inside the `app/` folder.

4. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## Testing

Run tests with pytest:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=app tests/
```

## API Endpoints

### Health Check
- **GET** `/health` - Returns the health status of the API
  ```json
  {
    "status": "ok"
  }
  ```

## Development

The project uses:
- **FastAPI** - Modern web framework for building APIs
- **SQLAlchemy** - SQL toolkit and ORM
- **Pydantic** - Data validation using Python type annotations
- **Uvicorn** - ASGI server
- **Pytest** - Testing framework

## Next Steps

- [ ] Add database models
- [ ] Implement authentication
- [ ] Create API endpoints for train scheduling
- [ ] Add more comprehensive tests

