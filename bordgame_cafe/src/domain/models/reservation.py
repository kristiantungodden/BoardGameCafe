"""Reservation domain model - Aggregate Root."""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from domain.exceptions import PartyTooLarge, OverlappingReservation, InvalidReservationStatus


class ReservationStatus(str, Enum):
    """Status of a reservation."""
    
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    SEATED = "seated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Reservation(BaseModel):
    """
    Reservation aggregate root.
    
    Invariants:
    - party_size must be <= table capacity
    - no overlapping reservations on same table/time window
    - status transitions must be valid
    """
    
    id: Optional[int] = None
    customer_id: int
    table_id: int
    party_size: int
    reserved_at: datetime
    reserved_until: datetime
    status: ReservationStatus = ReservationStatus.SUBMITTED
    special_requests: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        return f"Reservation {self.id} - Table {self.table_id} - {self.party_size} people"
    
    # Aggregate methods for invariant enforcement
    
    def validate_capacity(self, table_capacity: int) -> None:
        """
        Validate that party size doesn't exceed table capacity.
        
        Raises:
            PartyTooLarge: If party size > table capacity
        """
        if self.party_size > table_capacity:
            raise PartyTooLarge(
                f"Party size {self.party_size} exceeds table capacity {table_capacity}"
            )
    
    def check_overlap(self, other_reservations: list["Reservation"]) -> None:
        """
        Check for overlapping reservations on the same table.
        
        Raises:
            OverlappingReservation: If reservation overlaps with existing ones
        """
        for other in other_reservations:
            if other.status in [ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW]:
                continue  # Skip cancelled/no-show reservations
            
            # Check for time overlap: self.reserved_at < other.reserved_until AND self.reserved_until > other.reserved_at
            if self.reserved_at < other.reserved_until and self.reserved_until > other.reserved_at:
                raise OverlappingReservation(
                    f"Reservation overlaps with existing reservation {other.id}"
                )
    
    def confirm(self) -> None:
        """Confirm a submitted reservation."""
        if self.status != ReservationStatus.SUBMITTED:
            raise InvalidReservationStatus(
                f"Cannot confirm reservation with status {self.status}"
            )
        self.status = ReservationStatus.CONFIRMED
        self.updated_at = datetime.utcnow()
    
    def seat(self) -> None:
        """Mark reservation as seated."""
        if self.status not in [ReservationStatus.CONFIRMED]:
            raise InvalidReservationStatus(
                f"Cannot seat reservation with status {self.status}"
            )
        self.status = ReservationStatus.SEATED
        self.updated_at = datetime.utcnow()
    
    def complete(self) -> None:
        """Mark reservation as completed."""
        if self.status != ReservationStatus.SEATED:
            raise InvalidReservationStatus(
                f"Cannot complete reservation with status {self.status}"
            )
        self.status = ReservationStatus.COMPLETED
        self.updated_at = datetime.utcnow()
    
    def cancel(self) -> None:
        """Cancel a reservation."""
        if self.status in [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW]:
            raise InvalidReservationStatus(
                f"Cannot cancel reservation with status {self.status}"
            )
        self.status = ReservationStatus.CANCELLED
        self.updated_at = datetime.utcnow()
    
    def mark_no_show(self) -> None:
        """Mark reservation as no-show."""
        if self.status not in [ReservationStatus.CONFIRMED, ReservationStatus.SEATED]:
            raise InvalidReservationStatus(
                f"Cannot mark no-show for reservation with status {self.status}"
            )
        self.status = ReservationStatus.NO_SHOW
        self.updated_at = datetime.utcnow()
