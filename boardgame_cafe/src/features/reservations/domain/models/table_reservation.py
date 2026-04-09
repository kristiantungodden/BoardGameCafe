"""Domain model for TableReservation.

The TableReservation entity is a link between a Booking and a Table.
It is similar to GameReservation, which links Bookings to GameCopies.

This is NOT the same as the old TableReservation which used to contain
the booking data itself. The booking data is now in the Booking entity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.domain.exceptions import ValidationError


@dataclass
class TableReservation:
    """Domain entity for a table reservation link.
    
    This entity links a Booking to a specific Table.
    It is the join entity between Booking and Table, similar to how
    GameReservation is the join entity between Booking and GameCopy.
    """
    
    booking_id: int
    table_id: int
    id: Optional[int] = None
    
    def __post_init__(self) -> None:
        self._validate()
    
    def _validate(self) -> None:
        if self.booking_id <= 0:
            raise ValidationError("booking_id must be a positive integer")
        if self.table_id <= 0:
            raise ValidationError("table_id must be a positive integer")
