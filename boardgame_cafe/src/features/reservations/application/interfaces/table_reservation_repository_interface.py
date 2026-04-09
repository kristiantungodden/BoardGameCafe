"""Interface for TableReservationRepository.

Defines the contract for any repository implementation that persists table reservations.
"""
from abc import ABC, abstractmethod
from typing import Optional, Sequence

from features.reservations.domain.models.table_reservation import TableReservation


class TableReservationRepositoryInterface(ABC):
    """Interface for table reservation link persistence."""
    
    @abstractmethod
    def save(self, table_reservation: TableReservation) -> TableReservation:
        """Save a new table reservation link. Returns with id assigned."""
    
    @abstractmethod
    def get_by_id(self, table_reservation_link_id: int) -> Optional[TableReservation]:
        """Get a table reservation by id. Returns None if not found."""
    
    @abstractmethod
    def delete(self, table_reservation_link_id: int) -> None:
        """Delete a table reservation by id."""
    
    @abstractmethod
    def list_by_booking_id(self, booking_id: int) -> Sequence[TableReservation]:
        """List all table reservations for a booking."""
    
    @abstractmethod
    def get_by_booking_and_table(
        self, booking_id: int, table_id: int
    ) -> Optional[TableReservation]:
        """Get a table reservation by booking_id and table_id. Returns None if not found."""
