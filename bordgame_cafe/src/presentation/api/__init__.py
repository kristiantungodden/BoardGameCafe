"""API package with blueprint registration."""

from .auth import auth_bp
from .games import games_bp
from .tables import tables_bp
from .reservations import reservations_bp
from .steward import steward_bp
from .admin import admin_bp

__all__ = [
    "auth_bp",
    "games_bp",
    "tables_bp",
    "reservations_bp",
    "steward_bp",
    "admin_bp",
]
