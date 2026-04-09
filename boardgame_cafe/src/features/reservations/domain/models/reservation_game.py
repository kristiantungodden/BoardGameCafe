"""Domain model for GameReservation.

The GameReservation entity is a link between a Booking and a GameCopy.
It replaces the old pattern where games were reserved per table-reservation.
Now games are reserved per booking, since a booking can use multiple tables.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.domain.exceptions import ValidationError


@dataclass
class ReservationGame:
    """Domain entity for a game reservation link.
    
    Links a Booking to a specific GameCopy that was requested/reserved for this booking.
    This is separate from the table assignment - games are booked per booking,
    not per specific table.
    """
    
    booking_id: int
    requested_game_id: int
    game_copy_id: int
    id: Optional[int] = None

    def __post_init__(self) -> None:
        if self.booking_id <= 0:
            raise ValidationError("booking_id must be a positive integer")
        if self.requested_game_id <= 0:
            raise ValidationError("requested_game_id must be a positive integer")
        if self.game_copy_id <= 0:
            raise ValidationError("game_copy_id must be a positive integer")
