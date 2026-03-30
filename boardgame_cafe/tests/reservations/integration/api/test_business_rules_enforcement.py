"""
Business Rules Enforcement Tests - Integration Tests for Domain Constraints

These tests enforce critical business rules at API boundaries:
- Opening hours: 09:00 to 23:00 only
- Auto-assignment algorithm determinism
- Availability suggestions match auto-selection
"""

import pytest
from datetime import datetime

from tests.reservations.test_fixtures import FakeCurrentUser


class TestOpeningHoursEnforcement:
	"""Tests enforcing the business rule: cafe only opens 09:00-23:00."""
	
	def test_booking_before_opening_hour_rejected(self, app, test_data):
		"""
		REQUIREMENT: Bookings starting before 09:00 MUST be rejected.
		This is a hard business rule that cannot be bypassed.
		"""
		from unittest.mock import patch
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		from shared.domain.exceptions import ValidationError
		
		user_id = test_data["user"]["id"]
		
		with app.app_context():
			user_logged_in = FakeCurrentUser(user_id=user_id, is_authenticated=True)
			handler = get_create_booking_handler()
			
			# Try to book at 08:30 (before opening)
			with pytest.raises(ValidationError) as exc:
				handler(
					CreateReservationCommand(
						customer_id=user_id,
						table_id=None,
						start_ts=datetime(2026, 3, 30, 8, 30),  # Before 09:00
						end_ts=datetime(2026, 3, 30, 10, 0),
						party_size=4,
					),
					games=[]
				)
			
			error_msg = str(exc.value).lower()
			assert "opening" in error_msg or "09" in error_msg or "hours" in error_msg, (
				f"Error should mention opening hours, got: {exc.value}"
			)
	
	def test_booking_after_closing_hour_rejected(self, app, test_data):
		"""
		REQUIREMENT: Bookings ending after 23:00 MUST be rejected.
		This is a hard business rule that cannot be bypassed.
		"""
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		from shared.domain.exceptions import ValidationError
		
		user_id = test_data["user"]["id"]
		
		with app.app_context():
			handler = get_create_booking_handler()
			
			# Try to book until 23:30 (after closing)
			with pytest.raises(ValidationError) as exc:
				handler(
					CreateReservationCommand(
						customer_id=user_id,
						table_id=None,
						start_ts=datetime(2026, 3, 30, 22, 0),
						end_ts=datetime(2026, 3, 30, 23, 30),  # After 23:00
						party_size=4,
					),
					games=[]
				)
			
			error_msg = str(exc.value).lower()
			assert "opening" in error_msg or "23" in error_msg or "hours" in error_msg, (
				f"Error should mention opening hours, got: {exc.value}"
			)
	
	def test_booking_at_opening_hour_accepted(self, app, test_data):
		"""REQUIREMENT: Bookings starting at exactly 09:00 should be accepted."""
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		
		user_id = test_data["user"]["id"]
		
		with app.app_context():
			handler = get_create_booking_handler()
			
			# This should NOT raise
			result = handler(
				CreateReservationCommand(
					customer_id=user_id,
					table_id=None,
					start_ts=datetime(2026, 3, 30, 9, 0),  # Exactly at opening
					end_ts=datetime(2026, 3, 30, 11, 0),
					party_size=4,
				),
				games=[]
			)
			
			assert result[0].start_ts.hour == 9
	
	def test_booking_until_closing_hour_accepted(self, app, test_data):
		"""REQUIREMENT: Bookings ending at exactly 23:00 should be accepted."""
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		
		user_id = test_data["user"]["id"]
		
		with app.app_context():
			handler = get_create_booking_handler()
			
			# This should NOT raise
			result = handler(
				CreateReservationCommand(
					customer_id=user_id,
					table_id=None,
					start_ts=datetime(2026, 3, 30, 21, 0),
					end_ts=datetime(2026, 3, 30, 23, 0),  # Exactly at closing
					party_size=4,
				),
				games=[]
			)
			
			assert result[0].end_ts.hour == 23


class TestAutoAssignmentLogic:
	"""
	Tests ensuring auto-assignment logic follows predictable, deterministic rules.
	
	RULES:
	1. Suggested table from /availability endpoint must be the one auto-selected
	2. Auto-selected table must be smallest that fits party_size
	3. Auto-selected copy must be first available by ID
	"""
	
	def test_availability_suggestion_matches_auto_selection(self, app, test_data):
		"""
		REQUIREMENT: GET /api/reservations/availability should suggest the SAME table
		that will be auto-assigned when creating a booking with the same parameters.
		
		This ensures API is honest about what will actually happen.
		"""
		from shared.presentation.api.deps import get_booking_availability_handler
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		
		with app.app_context():
			# Get availability suggestion
			availability_handler = get_booking_availability_handler()
			availability = availability_handler(
				datetime(2026, 3, 30, 18, 0),
				datetime(2026, 3, 30, 20, 0),
				4  # party_size
			)
			
			suggested_table_id = availability["suggested_table"]["id"]
			
			# Create booking with auto-selection
			booking_handler = get_create_booking_handler()
			reservation, _, _ = booking_handler(
				CreateReservationCommand(
					customer_id=test_data["user"]["id"],
					table_id=None,  # Auto-select
					start_ts=datetime(2026, 3, 30, 18, 0),
					end_ts=datetime(2026, 3, 30, 20, 0),
					party_size=4,
				),
				games=[]
			)
			
			assert reservation.table_id == suggested_table_id, (
				f"Auto-assigned table {reservation.table_id} should match "
				f"suggested table {suggested_table_id} from availability endpoint"
			)
	
	def test_auto_selection_chooses_smallest_fitting_table(self, app, test_data):
		"""
		REQUIREMENT: When auto-selecting a table, choose the SMALLEST table 
		that has capacity >= party_size.
		
		Example: For party_size=4:
		- Table A (capacity 4) <- SELECT THIS
		- Table B (capacity 6)
		- Table C (capacity 8)
		"""
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		
		with app.app_context():
			handler = get_create_booking_handler()
			
			# test_data has:
			# - Table 1: capacity 4
			# - Table 2: capacity 6
			
			# Request party of 4: should get Table 1 (capacity 4), not Table 2 (capacity 6)
			reservation, _, _ = handler(
				CreateReservationCommand(
					customer_id=test_data["user"]["id"],
					table_id=None,
					start_ts=datetime(2026, 3, 30, 18, 0),
					end_ts=datetime(2026, 3, 30, 20, 0),
					party_size=4,
				),
				games=[]
			)
			
			# Should be table 1 (capacity 4)
			assert reservation.table_id == test_data["tables"][0]["id"], (
				f"Should select smallest fitting table. Tables: {test_data['tables']}, "
				f"Selected: {reservation.table_id}"
			)
	
	def test_auto_selection_chooses_first_available_copy_by_id(self, app, test_data):
		"""
		REQUIREMENT: When auto-selecting a game copy, choose the one with the 
		LOWEST ID among available copies.
		
		This ensures deterministic, reproducible behavior.
		"""
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		
		game_id = test_data["games"][0]["id"]
		
		with app.app_context():
			handler = get_create_booking_handler()
			
			# test_data creates copies with IDs in order
			# Copy order: copy1 (game 1), copy2 (game 1), copy3 (game 2)
			
			reservation, games, _ = handler(
				CreateReservationCommand(
					customer_id=test_data["user"]["id"],
					table_id=None,
					start_ts=datetime(2026, 3, 30, 18, 0),
					end_ts=datetime(2026, 3, 30, 20, 0),
					party_size=4,
				),
				games=[{"requested_game_id": game_id}]  # Request first game (Catan)
			)
			
			assert len(games) == 1, f"Should have 1 game reservation, got {len(games)}"
			
			# Should get the first available copy (lowest ID)
			first_copy_id = test_data["copies"][0]["id"]
			assert games[0].game_copy_id == first_copy_id, (
				f"Should select first available copy. Copies: {test_data['copies']}, "
				f"Selected: {games[0].game_copy_id}"
			)
	
	def test_auto_selection_respects_existing_bookings(self, app, test_data):
		"""
		REQUIREMENT: Auto-selection must skip tables/copies already booked 
		during the requested time window.
		"""
		from shared.presentation.api.deps import get_create_booking_handler
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationCommand
		)
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from features.reservations.domain.models.reservation import TableReservation
		
		table1_id = test_data["tables"][0]["id"]
		table2_id = test_data["tables"][1]["id"]
		user_id = test_data["user"]["id"]
		
		with app.app_context():
			# Block Table 1 during the requested time
			repo = SqlAlchemyReservationRepository()
			blocking_res = TableReservation(
				customer_id=999,
				table_id=table1_id,
				start_ts=datetime(2026, 3, 30, 18, 0),
				end_ts=datetime(2026, 3, 30, 20, 0),
				party_size=10,
				status="confirmed",
			)
			repo.add(blocking_res)
			
			# Auto-select should skip Table 1 and pick Table 2
			handler = get_create_booking_handler()
			reservation, _, _ = handler(
				CreateReservationCommand(
					customer_id=user_id,
					table_id=None,  # Auto-select
					start_ts=datetime(2026, 3, 30, 18, 0),
					end_ts=datetime(2026, 3, 30, 20, 0),
					party_size=4,
				),
				games=[]
			)
			
			assert reservation.table_id == table2_id, (
				f"Should skip blocked Table 1 ({table1_id}) and pick Table 2 ({table2_id}), "
				f"got {reservation.table_id}"
			)
