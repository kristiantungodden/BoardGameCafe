"""
Unit tests for the Booking domain model owned by the bookings feature.
"""
from datetime import datetime, timezone

import pytest

from features.bookings.domain.models.booking import Booking
from shared.domain.exceptions import InvalidStatusTransition, ValidationError


class TestBookingCreation:
    def test_create_booking_with_required_fields_succeeds(self):
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )

        assert booking.customer_id == 1
        assert booking.party_size == 4
        assert booking.status == "created"
        assert booking.notes is None
        assert booking.id is None
        assert booking.created_at is not None

    def test_create_booking_with_existing_id_succeeds(self):
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
            id=42,
        )

        assert booking.id == 42


class TestBookingValidation:
    def test_booking_rejects_non_positive_customer_id(self):
        with pytest.raises(ValidationError, match="customer_id must be a positive integer"):
            Booking(
                customer_id=0,
                start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
                end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
                party_size=4,
            )

    def test_booking_rejects_non_positive_party_size(self):
        with pytest.raises(ValidationError, match="party_size must be a positive integer"):
            Booking(
                customer_id=1,
                start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
                end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
                party_size=0,
            )

    def test_booking_rejects_invalid_time_window(self):
        start = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="end_ts must be after start_ts"):
            Booking(
                customer_id=1,
                start_ts=start,
                end_ts=start,
                party_size=4,
            )


class TestBookingStatusTransitions:
    def test_booking_can_seat_cancel_complete_no_show(self):
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking.confirm()
        booking.seat()
        assert booking.status == "seated"

        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking.confirm()
        booking.cancel()
        assert booking.status == "cancelled"

        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
            status="seated",
        )
        booking.complete()
        assert booking.status == "completed"

        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking.confirm()
        booking.mark_no_show()
        assert booking.status == "no_show"

    def test_booking_rejects_invalid_transition(self):
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
            status="completed",
        )
        with pytest.raises(InvalidStatusTransition):
            booking.seat()


class TestBookingOverlaps:
    """Test suite for Booking overlap detection business logic."""
    
    def test_overlapping_bookings_same_customer(self):
        """RULE: Bookings overlap if time ranges intersect and same customer."""
        booking1 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking2 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 19, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 21, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        
        assert booking1.overlaps(booking2) is True
        assert booking2.overlaps(booking1) is True
    
    def test_non_overlapping_bookings_same_customer(self):
        """RULE: Bookings don't overlap if time ranges don't intersect."""
        booking1 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking2 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 22, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        
        assert booking1.overlaps(booking2) is False
        assert booking2.overlaps(booking1) is False
    
    def test_overlapping_bookings_different_customers(self):
        """RULE: Bookings with different customers never overlap."""
        booking1 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking2 = Booking(
            customer_id=2,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        
        assert booking1.overlaps(booking2) is False
        assert booking2.overlaps(booking1) is False
    
    def test_booking_does_not_overlap_with_self(self):
        """RULE: A booking overlaps with itself (same customer, same time)."""
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        
        assert booking.overlaps(booking) is True
    
    def test_booking_adjacent_times_do_not_overlap(self):
        """RULE: Bookings with adjacent times (end == start) do not overlap."""
        booking1 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 19, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking2 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 19, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        
        assert booking1.overlaps(booking2) is False
        assert booking2.overlaps(booking1) is False
    
    def test_booking_fully_contained_overlaps(self):
        """RULE: A booking fully contained within another overlaps."""
        booking1 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 22, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        booking2 = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 19, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 21, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        
        assert booking1.overlaps(booking2) is True
        assert booking2.overlaps(booking1) is True


class TestBookingEdgeCases:
    """Test suite for Booking edge cases and boundary conditions."""
    
    def test_booking_with_notes(self):
        """RULE: Booking can have optional notes."""
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
            notes="Window seat preferred",
        )
        
        assert booking.notes == "Window seat preferred"
    
    def test_booking_with_large_party_size(self):
        """RULE: Booking accepts large party sizes."""
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=100,
        )
        
        assert booking.party_size == 100
    
    def test_booking_with_long_duration(self):
        """RULE: Booking accepts long durations."""
        from datetime import timedelta
        start = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=12)
        
        booking = Booking(
            customer_id=1,
            start_ts=start,
            end_ts=end,
            party_size=4,
        )
        
        assert booking.start_ts == start
        assert booking.end_ts == end
    
    def test_booking_status_transitions_are_sequential(self):
        """RULE: Status transitions must follow the defined sequence."""
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        
        # Cannot seat without confirming first
        with pytest.raises(InvalidStatusTransition):
            booking.seat()
        
        # Confirm first
        booking.confirm()
        
        # Cannot confirm again
        with pytest.raises(InvalidStatusTransition):
            booking.confirm()
        
        # Now can seat
        booking.seat()
        assert booking.status == "seated"
        
        # Cannot cancel after seating
        with pytest.raises(InvalidStatusTransition):
            booking.cancel()
        
        # Complete the booking
        booking.complete()
        assert booking.status == "completed"
        
        # Cannot do anything after completion
        with pytest.raises(InvalidStatusTransition):
            booking.complete()
    
    def test_booking_cannot_confirm_from_created_status_only(self):
        """RULE: Only bookings in 'created' status can be confirmed."""
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
            status="confirmed",
        )
        
        with pytest.raises(InvalidStatusTransition):
            booking.confirm()
    
    def test_booking_created_at_is_set_automatically(self):
        """RULE: created_at is automatically set on creation."""
        before = datetime.now(timezone.utc)
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        after = datetime.now(timezone.utc)
        
        assert booking.created_at >= before
        assert booking.created_at <= after
