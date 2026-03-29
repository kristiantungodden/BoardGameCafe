"""
Model registry: Ensures all ORM model classes are imported and registered with SQLAlchemy
before mapper configuration runs.

When using string-based relationships (e.g., relationship("TableDB")), SQLAlchemy's mapper
requires all target classes to be registered before the first query or create_all() call.
This module centralizes model imports to make the bootstrap intent explicit and maintainable.

Usage:
    from shared.infrastructure.database.model_registry import register_all_models
    
    register_all_models()  # Call once at app startup, before any ORM queries
"""


def register_all_models() -> None:
    """
    Register all ORM model classes with SQLAlchemy's mapper registry.
    
    This function's only purpose is its side effect: importing all model classes
    ensures they are registered and string-based relationships can be resolved.
    Call this once at application startup, before any ORM queries or db.create_all().
    """
    # Import all ORM model classes. Order does not matter; imports are idempotent.
    # pylint: disable=unused-import
    from features.users.infrastructure.database import UserDB
    from features.tables.infrastructure.database import TableDB
    from features.reservations.infrastructure.database import TableReservation, GameReservation
    from features.games.infrastructure.database import (
        GameDB,
        GameCopyDB,
        GameTagDB,
        GameTagLinkDB,
        GameRatingDB,
    )
    from features.payments.infrastructure.database import PaymentDB
