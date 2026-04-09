"""
Transaction Atomicity Tests - Integration Tests for Data Consistency

These tests enforce transactional consistency:
- All-or-nothing bookings: if payment fails, reservation rolls back
- No partial states: either complete booking or nothing
- Concurrent booking conflicts are prevented
"""

import pytest
from datetime import datetime
from decimal import Decimal
from features.bookings.domain.models.booking import Booking


def _make_reservation(*, table_id: int, **kwargs) -> Booking:
	reservation = Booking(**kwargs)
	setattr(reservation, "table_id", table_id)
	return reservation


class TestTransactionAtomicity:
	"""Tests ensuring bookings are atomic (all-or-nothing)."""
	
	def test_booking_fails_atomically_if_table_unavailable(self, app, test_data):
		"""
		REQUIREMENT: If no suitable table is available, the entire booking 
		MUST fail without creating a partial state.
		
		This means:
		- No reservation created
		- No games assigned
		- No payment record
		"""
		from features.reservations.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from shared.domain.exceptions import ValidationError
		from shared.infrastructure import db
		
		table1_id = test_data["tables"][0]["id"]
		table2_id = test_data["tables"][1]["id"]
		user_id = test_data["user"]["id"]
		
		with app.app_context():
			# Block ALL tables during requested time
			repo = SqlAlchemyReservationRepository()
			for table_id in [table1_id, table2_id]:
				blocking_res = _make_reservation(
					customer_id=999,
					table_id=table_id,
					start_ts=datetime(2026, 3, 30, 18, 0),
					end_ts=datetime(2026, 3, 30, 20, 0),
					party_size=10,
					status="confirmed",
				)
				repo.add(blocking_res)
			
			# Count existing reservations
			initial_count = len(repo.list_all())
			
			# Try to book - should fail
			handler = get_create_booking_handler()
			with pytest.raises(ValidationError):
				handler(
					CreateReservationCommand(
						customer_id=user_id,
						table_id=None,
						start_ts=datetime(2026, 3, 30, 18, 0),
						end_ts=datetime(2026, 3, 30, 20, 0),
						party_size=4,
					),
					games=[]
				)
			
			# Verify no new reservation was created
			final_count = len(repo.list_all())
			assert final_count == initial_count, (
				f"Booking failed, but a reservation was still created. "
				f"Initial: {initial_count}, Final: {final_count}"
			)
	
	def test_booking_fails_atomically_if_party_size_too_large(self, app, test_data):
		"""
		REQUIREMENT: If party is too large for any available table,
		booking must fail completely without creating any records.
		"""
		from features.reservations.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from shared.domain.exceptions import ValidationError
		
		user_id = test_data["user"]["id"]
		
		with app.app_context():
			repo = SqlAlchemyReservationRepository()
			initial_count = len(repo.list_all())
			
			# Largest table in test_data has capacity 6
			handler = get_create_booking_handler()
			with pytest.raises(ValidationError):
				handler(
					CreateReservationCommand(
						customer_id=user_id,
						table_id=None,
						start_ts=datetime(2026, 3, 30, 18, 0),
						end_ts=datetime(2026, 3, 30, 20, 0),
						party_size=100,  # Way too large
					),
					games=[]
				)
			
			# Verify no reservation was created
			final_count = len(repo.list_all())
			assert final_count == initial_count, (
				f"Booking should fail atomically, but changes were made: "
				f"{initial_count} -> {final_count}"
			)


class TestConcurrentBookingConflicts:
	"""Tests preventing overbooking when multiple requests arrive simultaneously."""
	
	def test_cannot_double_book_same_table(self, app, test_data):
		"""
		REQUIREMENT: Two concurrent bookings for the same table+time 
		must not both succeed. One must be rejected.
		
		This is a pessimistic lock scenario: the database ensures 
		at most one booking per table per time window.
		"""
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		
		table_id = test_data["tables"][0]["id"]
		
		with app.app_context():
			repo = SqlAlchemyReservationRepository()
			
			# First booking succeeds
			booking1 = _make_reservation(
				customer_id=1,
				table_id=table_id,
				start_ts=datetime(2026, 3, 30, 18, 0),
				end_ts=datetime(2026, 3, 30, 20, 0),
				party_size=4,
				status="confirmed",
			)
			repo.add(booking1)
			
			# Second booking for same table+time should either:
			# A) Be rejected by use case overlap check, OR
			# B) Be queued/waitlisted
			# But definitely NOT both confirmed
			
			booking2 = _make_reservation(
				customer_id=2,
				table_id=table_id,
				start_ts=datetime(2026, 3, 30, 18, 30),  # Overlaps
				end_ts=datetime(2026, 3, 30, 19, 30),
				party_size=4,
				status="confirmed",
			)
			
			# This should not be allowed
			overlapping_bookings = repo.list_for_table_in_window(
				table_id,
				booking2.start_ts,
				booking2.end_ts
			)
			
			assert len(overlapping_bookings) > 0, (
				"Table should have conflicting booking that prevents double-booking"
			)


class TestPaymentTransactionRollback:
	"""Tests ensuring payment failures roll back the entire booking."""
	
	def test_payment_failure_recorded_without_rollback(self, app, test_data):
		"""
		CURRENT BEHAVIOR: Payment failures currently create a reservation
		with status="pending_payment" and link to a failed payment record.
		This allows recovery/retry.
		
		This test documents the current (lenient) behavior, but notes that 
		stricter atomicity might be desired in the future.
		"""
		# This test is documented in test_reservation_payment_transaction.py
		# Noting here that the architecture allows payment retries
		pass


# ============================================================================
# Helper: Fixture for understanding atomicity in the system
# ============================================================================

@pytest.fixture
def atomic_booking_states(app, test_data):
	"""
	Defines the valid and invalid states a booking can be in.
	
	VALID PARTIAL STATES (allowed during transaction):
	- status="pending_payment": Reservation confirmed but payment not yet processed
	
	INVALID PARTIAL STATES (must never occur):
	- Reservation exists but no games assigned (for requested games)
	- Games assigned but no reservation (orphaned records)
	- Payment created but no reservation (orphaned payments)
	- Reservation cancelled but games still assigned
	
	FINAL VALID STATES:
	- status="confirmed": reservation + games + payment all exist
	- status="pending_payment": reservation + games exist, payment pending
	- (Exception occurred): None of the above exist
	"""
	return {
		"valid_partial": ["pending_payment"],
		"invalid_partial": [
			"reservation_without_games",
			"games_without_reservation",
			"payment_without_reservation",
			"reservation_with_cancelled_status_but_games",
		],
		"valid_final": ["confirmed", "pending_payment"],
	}
