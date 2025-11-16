from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import engine, Base
from app import models, schemas  # Import models to register them with Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - runs on startup and shutdown."""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup would go here if needed


app = FastAPI(
    title="Train Scheduler API",
    description="Railway scheduling system with time-based conflict detection",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=schemas.HealthCheckResponse)
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

