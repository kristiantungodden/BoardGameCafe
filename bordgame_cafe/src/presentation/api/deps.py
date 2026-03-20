"""Database session helpers for Flask routes."""

from infrastructure.database import SessionLocal
from infrastructure.repositories import (
    SQLAlchemyUserRepository,
    SQLAlchemyGameRepository,
    SQLAlchemyTableRepository,
    SQLAlchemyReservationRepository,
    SQLAlchemyPaymentRepository,
)


def get_user_repository():
    """Get user repository with a new session."""
    db = SessionLocal()
    return SQLAlchemyUserRepository(db)


def get_game_repository():
    """Get game repository with a new session."""
    db = SessionLocal()
    return SQLAlchemyGameRepository(db)


def get_table_repository():
    """Get table repository with a new session."""
    db = SessionLocal()
    return SQLAlchemyTableRepository(db)


def get_reservation_repository():
    """Get reservation repository with a new session."""
    db = SessionLocal()
    return SQLAlchemyReservationRepository(db)


def get_payment_repository():
    """Get payment repository with a new session."""
    db = SessionLocal()
    return SQLAlchemyPaymentRepository(db)
