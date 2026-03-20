"""Tests configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from infrastructure.database.models import Base


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine) -> Session:
    """Create a fresh database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "full_name": "Test User",
        "phone": "+1234567890",
        "password": "testpassword123",
        "role": "customer",
    }


@pytest.fixture
def test_game_data():
    """Test game data."""
    return {
        "title": "Test Game",
        "description": "A test game",
        "min_players": 2,
        "max_players": 4,
        "playtime_minutes": 45,
        "complexity_weight": 2.5,
        "tags": ["strategy", "fun"],
    }


@pytest.fixture
def test_table_data():
    """Test table data."""
    return {
        "number": 1,
        "capacity": 4,
        "location": "Main Hall",
        "features": ["power_outlet"],
    }
