"""
Unit tests for TableReservationRepository interface contracts.

These tests define the expected behavior of any TableReservationRepository implementation.
"""
import pytest

from features.reservations.domain.models.table_reservation import TableReservation


class TableReservationRepositoryContract:
    """Interface contract tests for TableReservationRepository implementations."""
    
    def get_repository(self):
        """Subclasses must implement this to provide a repository instance."""
        raise NotImplementedError("Subclasses must implement get_repository()")
    
    def test_save_table_reservation_and_retrieve_by_id(self):
        """REQUIREMENT: Repository can save a table reservation and retrieve it by id."""
        repo = self.get_repository()
        
        table_res = TableReservation(
            booking_id=1,
            table_id=5,
        )
        
        saved = repo.save(table_res)
        assert saved.id is not None
        
        retrieved = repo.get_by_id(saved.id)
        assert retrieved is not None
        assert retrieved.booking_id == 1
        assert retrieved.table_id == 5
    
    def test_find_table_reservation_by_booking_id(self):
        """REQUIREMENT: Repository can find all table reservations for a booking."""
        repo = self.get_repository()
        
        table_res1 = TableReservation(
            booking_id=1,
            table_id=5,
        )
        table_res2 = TableReservation(
            booking_id=2,
            table_id=7,
        )
        
        repo.save(table_res1)
        repo.save(table_res2)
        
        booking1_tables = repo.list_by_booking_id(1)
        
        assert len(booking1_tables) >= 1
        assert any(t.booking_id == 1 and t.table_id == 5 for t in booking1_tables)
    
    def test_find_table_reservation_by_booking_and_table(self):
        """REQUIREMENT: Repository can find a specific table reservation by booking_id and table_id."""
        repo = self.get_repository()
        
        table_res = TableReservation(
            booking_id=1,
            table_id=5,
        )
        
        saved = repo.save(table_res)
        
        retrieved = repo.get_by_booking_and_table(1, 5)
        
        assert retrieved is not None
        assert retrieved.booking_id == 1
        assert retrieved.table_id == 5
    
    def test_get_by_id_returns_none_for_missing_table_reservation(self):
        """REQUIREMENT: Repository returns None when table reservation id doesn't exist."""
        repo = self.get_repository()
        
        result = repo.get_by_id(99999)
        
        assert result is None
    
    def test_delete_table_reservation(self):
        """REQUIREMENT: Repository can delete a table reservation."""
        repo = self.get_repository()
        
        table_res = TableReservation(
            booking_id=1,
            table_id=5,
        )
        
        saved = repo.save(table_res)
        repo.delete(saved.id)
        
        retrieved = repo.get_by_id(saved.id)
        assert retrieved is None
    
    def test_get_by_booking_and_table_returns_none_for_missing(self):
        """REQUIREMENT: Repository returns None when booking_id/table_id combination doesn't exist."""
        repo = self.get_repository()
        
        result = repo.get_by_booking_and_table(99999, 99999)
        
        assert result is None
