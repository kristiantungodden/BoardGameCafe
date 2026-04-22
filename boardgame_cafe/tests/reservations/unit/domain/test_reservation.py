"""
Domain Model Tests - Unit Tests for Reservation Invariants

These tests ensure domain models enforce their own constraints.
Domain models MUST validate invariants and reject invalid states.
"""

from datetime import datetime, timedelta

import pytest
from features.bookings.domain.models.booking import Booking
from shared.domain.exceptions import InvalidStatusTransition, ValidationError


def _make_reservation(*, table_id: int, **kwargs) -> Booking:
	reservation = Booking(**kwargs)
	setattr(reservation, "table_id", table_id)
	return reservation


# ============================================================================
# Status Transition Tests
# ============================================================================

def test_reservation_seat_changes_status_to_seated():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = _make_reservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	reservation.confirm()
	reservation.seat()

	assert reservation.status == "seated"


def test_reservation_complete_changes_status_to_completed():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = _make_reservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	reservation.confirm()
	reservation.seat()
	reservation.complete()

	assert reservation.status == "completed"


def test_reservation_no_show_changes_status_to_no_show():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = _make_reservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	reservation.confirm()
	reservation.mark_no_show()

	assert reservation.status == "no_show"


def test_reservation_cannot_complete_without_being_seated():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = _make_reservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	try:
		reservation.complete()
		assert False, "Expected InvalidStatusTransition"
	except InvalidStatusTransition:
		assert True


# ============================================================================
# Domain Model Invariant Tests
# ============================================================================
# These tests ensure the domain model REJECTS invalid data at construction time.
# This is critical: the domain model is the last line of defense for invariants.


def test_reservation_rejects_negative_party_size():
	"""INVARIANT: party_size MUST be positive (> 0)."""
	with pytest.raises(ValidationError) as exc:
		Booking(
			customer_id=1,
			start_ts=datetime(2026, 3, 30, 18, 0),
			end_ts=datetime(2026, 3, 30, 20, 0),
			party_size=-1,  # Invalid: negative
		)
	
	assert "party_size" in str(exc.value).lower() or "positive" in str(exc.value).lower()


def test_reservation_rejects_zero_party_size():
	"""INVARIANT: party_size MUST be positive (> 0)."""
	with pytest.raises(ValidationError) as exc:
		Booking(
			customer_id=1,
			start_ts=datetime(2026, 3, 30, 18, 0),
			end_ts=datetime(2026, 3, 30, 20, 0),
			party_size=0,  # Invalid: zero
		)
	
	assert "party_size" in str(exc.value).lower() or "positive" in str(exc.value).lower()


def test_reservation_rejects_end_time_before_start_time():
	"""INVARIANT: end_ts MUST be > start_ts."""
	with pytest.raises(ValidationError) as exc:
		Booking(
			customer_id=1,
			start_ts=datetime(2026, 3, 30, 20, 0),
			end_ts=datetime(2026, 3, 30, 18, 0),  # Invalid: end before start
			party_size=4,
		)
	
	assert "end" in str(exc.value).lower() or "start" in str(exc.value).lower()


def test_reservation_rejects_end_time_equals_start_time():
	"""INVARIANT: end_ts MUST be > start_ts (not equal)."""
	with pytest.raises(ValidationError) as exc:
		Booking(
			customer_id=1,
			start_ts=datetime(2026, 3, 30, 18, 0),
			end_ts=datetime(2026, 3, 30, 18, 0),  # Invalid: same time
			party_size=4,
		)
	
	assert "end" in str(exc.value).lower() or "start" in str(exc.value).lower()


def test_reservation_rejects_invalid_status():
	"""INVARIANT: status MUST be from VALID_RESERVATION_STATUSES."""
	valid_statuses = {"created", "confirmed", "seated", "completed", "cancelled", "no_show"}
	invalid_statuses = ["draft", "pending", "pending_payment", "unknown_status", ""]
	
	for invalid_status in invalid_statuses:
		with pytest.raises(ValidationError) as exc:
			Booking(
				customer_id=1,
				start_ts=datetime(2026, 3, 30, 18, 0),
				end_ts=datetime(2026, 3, 30, 20, 0),
				party_size=4,
				status=invalid_status,
			)
		
		assert "status" in str(exc.value).lower(), \
			f"Expected status error for '{invalid_status}', got: {exc.value}"


def test_reservation_rejects_negative_customer_id():
	"""INVARIANT: customer_id MUST be positive."""
	with pytest.raises(ValidationError) as exc:
		Booking(
			customer_id=-1,  # Invalid
			start_ts=datetime(2026, 3, 30, 18, 0),
			end_ts=datetime(2026, 3, 30, 20, 0),
			party_size=4,
		)
	
	assert "customer_id" in str(exc.value).lower()


def test_booking_allows_link_metadata_for_table_id():
	"""table_id now belongs to reservation link ownership, not booking invariants."""
	reservation = _make_reservation(
		customer_id=1,
		table_id=-1,
		start_ts=datetime(2026, 3, 30, 18, 0),
		end_ts=datetime(2026, 3, 30, 20, 0),
		party_size=4,
	)

	assert reservation.table_id == -1

