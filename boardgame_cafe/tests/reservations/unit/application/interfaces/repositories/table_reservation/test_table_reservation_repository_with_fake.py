"""Unit tests for TableReservationRepository using a fake in-memory implementation."""
import pytest

from features.reservations.domain.models.table_reservation import TableReservation
from tests.reservations.unit.application.interfaces.repositories.table_reservation.test_table_reservation_repository_contract import (
    TableReservationRepositoryContract,
)


class FakeTableReservationRepository:
    """In-memory fake implementation of TableReservationRepository for testing."""
    
    def __init__(self):
        self._table_reservations = {}
        self._next_id = 1
    
    def save(self, table_reservation: TableReservation) -> TableReservation:
        """Save a new table reservation link."""
        table_reservation.id = self._next_id
        self._next_id += 1
        self._table_reservations[table_reservation.id] = table_reservation
        return table_reservation
    
    def get_by_id(self, table_reservation_link_id: int):
        """Get a table reservation by id."""
        return self._table_reservations.get(table_reservation_link_id)
    
    def delete(self, table_reservation_link_id: int) -> None:
        """Delete a table reservation by id."""
        if table_reservation_link_id in self._table_reservations:
            del self._table_reservations[table_reservation_link_id]
    
    def list_by_booking_id(self, booking_id: int):
        """List all table reservations for a booking."""
        return [
            tr for tr in self._table_reservations.values()
            if tr.booking_id == booking_id
        ]
    
    def get_by_booking_and_table(self, booking_id: int, table_id: int):
        """Get a table reservation by booking_id and table_id."""
        for tr in self._table_reservations.values():
            if tr.booking_id == booking_id and tr.table_id == table_id:
                return tr
        return None


class TestTableReservationRepositoryWithFakeImpl(TableReservationRepositoryContract):
    """Test TableReservationRepository contract with fake in-memory implementation."""
    
    def get_repository(self):
        """Return a fake repository instance."""
        return FakeTableReservationRepository()
