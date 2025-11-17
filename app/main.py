from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from app.db import engine, Base
from app import models, schemas  # Import models to register them with Base
from app.api import stations, trains, segments, trips


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

# API v1 router
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(stations.router)
api_v1_router.include_router(trains.router)
api_v1_router.include_router(segments.router)
api_v1_router.include_router(trips.router)

# Include the v1 router in the app
app.include_router(api_v1_router)


@app.get("/health", response_model=schemas.HealthCheckResponse)
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

