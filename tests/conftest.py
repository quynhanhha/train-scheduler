"""
Shared test fixtures and configuration.

This file is automatically discovered by pytest and makes fixtures
available to all test files without explicit imports.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.main import app
from app.db import Base, get_db
from app import models  # Import models to register with Base


def get_test_db_url(test_name: str) -> str:
    """Generate test database URL based on test module name."""
    return f"sqlite:///./test_{test_name}.db"


def create_test_engine_and_session(db_url: str):
    """Create test engine and session maker."""
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestingSessionLocal


@pytest.fixture(scope="session")
def test_db_setup(request):
    """
    Session-scoped fixture to set up test database infrastructure.
    
    This creates the engine and session maker once per test session.
    """
    # Get test module name to create unique DB file
    test_module = request.node.name
    db_url = get_test_db_url(test_module)
    
    engine, SessionLocal = create_test_engine_and_session(db_url)
    
    # Store in request for cleanup
    request.node.test_db_file = f"./test_{test_module}.db"
    
    return engine, SessionLocal


def make_override_get_db(SessionLocal):
    """Factory to create get_db override function."""
    def override_get_db():
        """Override database dependency for testing."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    return override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_test_database(request):
    """
    Module-scoped fixture to set up test database.
    
    Creates tables once per test module and cleans up after.
    """
    # Determine which test database to use based on the test module
    test_file = os.path.basename(request.fspath)
    test_name = test_file.replace("test_", "").replace(".py", "")
    
    db_url = get_test_db_url(test_name)
    db_file = f"./test_{test_name}.db"
    
    engine, SessionLocal = create_test_engine_and_session(db_url)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Override the get_db dependency
    override_func = make_override_get_db(SessionLocal)
    app.dependency_overrides[get_db] = override_func
    
    # Store session maker in module for use in clean_database fixture
    request.module._test_session_maker = SessionLocal
    
    yield SessionLocal
    
    # Teardown: drop tables and remove database file
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(db_file):
        os.remove(db_file)
    
    # Clean up dependency override
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


@pytest.fixture(autouse=True)
def clean_database(request):
    """
    Function-scoped fixture to clean database between tests.
    
    Deletes all data from all tables before each test to ensure isolation.
    """
    # Get the session maker from the module
    SessionLocal = request.module._test_session_maker
    
    session = SessionLocal()
    try:
        # Delete all data from all tables in reverse order (to handle foreign keys)
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
    
    yield  # Test runs here
    
    # Could add post-test cleanup here if needed


@pytest.fixture
def client():
    """
    Create a FastAPI test client.
    
    This client uses the overridden database dependency from setup_test_database.
    """
    return TestClient(app)

