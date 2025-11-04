"""Pytest configuration and shared fixtures"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh in-memory SQLite database for each test.
    Isolates tests from each other.
    """
    # Create in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """
    FastAPI test client with test database dependency override.
    """

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_subscriber(test_db):
    """Create sample subscriber for tests"""
    from app.models import Subscriber

    subscriber = Subscriber(
        buttondown_id="test-subscriber-id",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        status="active"
    )
    test_db.add(subscriber)
    test_db.commit()
    test_db.refresh(subscriber)
    return subscriber
