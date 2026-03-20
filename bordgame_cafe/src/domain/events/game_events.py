"""Game domain events."""

from datetime import datetime
from typing import Optional
from .domain_event import DomainEvent


class GameAssignedToReservation(DomainEvent):
    """Raised when a game is assigned to a reservation."""
    
    game_copy_id: int
    reservation_id: int
    assigned_by: int  # steward id


class GameCheckedOut(DomainEvent):
    """Raised when a game copy is checked out."""
    
    game_copy_id: int
    reservation_id: int
    checked_out_at: datetime
    checked_out_by: int  # steward id


class GameReturned(DomainEvent):
    """Raised when a game is returned."""
    
    game_copy_id: int
    reservation_id: int
    returned_at: datetime
    returned_by: int  # steward id


class DamageReported(DomainEvent):
    """Raised when damage is reported on a game copy."""
    
    game_copy_id: int
    severity: str  # minor, moderate, severe
    description: str
    reported_by: int  # steward id
