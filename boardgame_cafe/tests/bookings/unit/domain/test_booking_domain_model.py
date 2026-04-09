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
        assert booking.status == "confirmed"
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
        booking.seat()
        assert booking.status == "seated"

        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
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
