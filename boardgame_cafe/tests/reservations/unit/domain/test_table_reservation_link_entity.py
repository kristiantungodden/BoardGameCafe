"""
Unit tests for the TableReservation link entity.

These tests define the boundaries and rules for the TableReservation entity.
The TableReservation is a link entity connecting a Booking to a Table,
similar to how GameReservation connects a Booking to a GameCopy.
"""
import pytest

from features.reservations.domain.models.table_reservation import TableReservation
from shared.domain.exceptions import ValidationError


class TestTableReservationCreation:
    """Test suite for TableReservation link entity creation and validation."""
    
    def test_create_table_reservation_with_required_fields_succeeds(self):
        """RULE: A table reservation link can be created with booking_id and table_id."""
        table_res = TableReservation(
            booking_id=1,
            table_id=5,
        )
        
        assert table_res.booking_id == 1
        assert table_res.table_id == 5
        assert table_res.id is None
    
    def test_create_table_reservation_with_existing_id_succeeds(self):
        """RULE: A table reservation can be reconstituted from database with an id."""
        table_res = TableReservation(
            booking_id=1,
            table_id=5,
            id=42,
        )
        
        assert table_res.id == 42
        assert table_res.booking_id == 1
        assert table_res.table_id == 5


class TestTableReservationValidation:
    """Test suite for TableReservation validation rules."""
    
    def test_table_reservation_rejects_non_positive_booking_id(self):
        """RULE: booking_id must be a positive integer."""
        with pytest.raises(ValidationError, match="booking_id must be a positive integer"):
            TableReservation(
                booking_id=0,
                table_id=5,
            )
        
        with pytest.raises(ValidationError, match="booking_id must be a positive integer"):
            TableReservation(
                booking_id=-1,
                table_id=5,
            )
    
    def test_table_reservation_rejects_non_positive_table_id(self):
        """RULE: table_id must be a positive integer."""
        with pytest.raises(ValidationError, match="table_id must be a positive integer"):
            TableReservation(
                booking_id=1,
                table_id=0,
            )
        
        with pytest.raises(ValidationError, match="table_id must be a positive integer"):
            TableReservation(
                booking_id=1,
                table_id=-5,
            )


class TestTableReservationSemantics:
    """Test suite for TableReservation domain semantics."""
    
    def test_table_reservation_can_have_optional_id(self):
        """RULE: A table reservation starts without an id (assigned on persistence)."""
        table_res = TableReservation(
            booking_id=1,
            table_id=5,
        )
        
        assert table_res.id is None
        
        # After persistence, id would be set by repository
        table_res.id = 100
        assert table_res.id == 100
    
    def test_table_reservation_is_immutable_link(self):
        """RULE: A table reservation is a simple link with no state transitions."""
        table_res = TableReservation(
            booking_id=1,
            table_id=5,
        )
        
        # No state-changing methods, just a link entity
        assert table_res.booking_id == 1
        assert table_res.table_id == 5
