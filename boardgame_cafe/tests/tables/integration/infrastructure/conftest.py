"""Shared fixtures for table repository tests."""
from shared.infrastructure import db
from features.tables.infrastructure.database import TableDB as CafeTableDB
from features.tables.domain.models.table import Table
from app import create_app
from features.tables.infrastructure.repositories import TableRepository

import pytest


@pytest.fixture(scope="module")
def app():
    """Provide a Flask app with testing config and app context."""
    app = create_app("testing")  # uses TestingConfig (sqlite:///:memory:)
    with app.app_context():
        db.create_all()  # create tables
        yield app
        db.session.remove()
        db.drop_all()  # cleanup


@pytest.fixture
def repo(app):
    """Provide a repository instance."""
    return TableRepository()


@pytest.fixture(autouse=True)
def reset_tables(app):
    """Ensure each test runs with a clean table dataset."""
    db.session.query(CafeTableDB).delete()
    db.session.commit()


def seed_tables(repo: TableRepository):
    """Create a standard 5-table dataset for filtering tests."""
    db.session.query(CafeTableDB).delete()
    db.session.commit()

    seeded = [
        Table(number=1, capacity=2, floor=1, zone="A", features={"near_window": True, "has_outlet": False}, status="available"),
        Table(number=2, capacity=4, floor=1, zone="A", features={"near_window": False, "has_outlet": True}, status="occupied"),
        Table(number=3, capacity=6, floor=2, zone="B", features={"near_window": True, "has_outlet": True}, status="available"),
        Table(number=4, capacity=8, floor=2, zone="B", features={"near_window": False, "has_outlet": False}, status="maintenance"),
        Table(number=5, capacity=4, floor=2, zone="C", features={"near_window": False, "has_outlet": False}, status="reserved"),
    ]
    return [repo.add(item) for item in seeded]
