from fastapi import FastAPI
from app.db import engine, Base
from app import models  # Import models to register them with Base

app = FastAPI(
    title="Train Scheduler API",
    description="Railway scheduling system with time-based conflict detection",
    version="1.0.0"
)


@app.on_event("startup")
def startup_event():
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

