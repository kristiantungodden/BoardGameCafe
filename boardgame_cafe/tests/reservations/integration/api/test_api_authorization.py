"""
API Authorization Boundary Tests - Integration Tests for Security

These tests enforce authorization at API boundaries:
- MUST enforce authentication on all endpoints
- MUST enforce authorization (access control) on data retrieval
- Non-staff users MUST only see their own reservations
- Staff users CAN see all reservations
- Non-owners MUST get 403 when accessing other users' data
"""

import pytest
from datetime import datetime, timedelta

from tests.reservations.test_fixtures import FakeCurrentUser


class TestAuthenticationBoundaries:
	"""Tests ensuring authentication is enforced at API layer."""
	
	def test_unauthenticated_get_reservations_returns_401(self, app):
		"""REQUIREMENT: GET /api/reservations without auth returns 401."""
		from unittest.mock import patch
		
		# Unauthenticated user
		unauthenticated = FakeCurrentUser(user_id=0, is_authenticated=False)
		
		with app.test_client() as client:
			with patch(
				'features.reservations.presentation.api.reservation_routes.current_user',
				unauthenticated
			):
				response = client.get("/api/reservations")
				assert response.status_code == 401, \
					f"Unauthenticated request should return 401, got {response.status_code}"
				data = response.get_json()
				assert "Authentication required" in data.get("error", ""), \
					f"Error should mention authentication, got: {data}"
	
	def test_unauthenticated_post_reservations_returns_401(self, app):
		"""REQUIREMENT: POST /api/reservations without auth returns 401."""
		from unittest.mock import patch
		
		unauthenticated = FakeCurrentUser(user_id=0, is_authenticated=False)
		
		with app.test_client() as client:
			with patch(
				'features.reservations.presentation.api.reservation_routes.current_user',
				unauthenticated
			):
				response = client.post(
					"/api/reservations",
					json={
						"start_ts": "2026-03-30T18:00:00",
						"end_ts": "2026-03-30T20:00:00",
						"party_size": 4,
					}
				)
				assert response.status_code == 401


class TestAuthorizationBoundaries:
	"""Tests ensuring authorization (access control) at API layer."""
	
	def test_non_staff_user_only_sees_their_own_reservations(self, app, test_data):
		"""
		REQUIREMENT: When a non-staff user GETs /api/reservations, 
		they should only see reservations where customer_id == their user_id.
		"""
		from unittest.mock import patch
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from features.reservations.domain.models.reservation import TableReservation
		from shared.infrastructure import db
		
		user1_id = test_data["user"]["id"]
		table_id = test_data["tables"][0]["id"]
		
		with app.app_context():
			# Create reservations for multiple users
			repo = SqlAlchemyReservationRepository()
			
			res_user1 = TableReservation(
				customer_id=user1_id,
				table_id=table_id,
				start_ts=datetime(2026, 3, 30, 18, 0),
				end_ts=datetime(2026, 3, 30, 20, 0),
				party_size=4,
			)
			res_user2 = TableReservation(
				customer_id=999,  # Different user
				table_id=table_id,
				start_ts=datetime(2026, 3, 31, 18, 0),
				end_ts=datetime(2026, 3, 31, 20, 0),
				party_size=4,
			)
			repo.add(res_user1)
			repo.add(res_user2)
			
			# User 1 requests their reservations
			user1_logged_in = FakeCurrentUser(user_id=user1_id, is_authenticated=True, is_staff=False)
			
			with app.test_client() as client:
				with patch(
					'features.reservations.presentation.api.reservation_routes.current_user',
					user1_logged_in
				):
					response = client.get("/api/reservations")
					assert response.status_code == 200
					data = response.get_json()
					
					# Should only contain reservations where customer_id == user1_id
					assert all(r["customer_id"] == user1_id for r in data), (
						f"Non-staff user should only see their own reservations. "
						f"Got: {data}"
					)
	
	def test_non_staff_user_cannot_read_other_users_reservation(self, app, test_data):
		"""
		REQUIREMENT: When a non-staff user tries to GET a reservation they don't own,
		they should get 403 Forbidden.
		"""
		from unittest.mock import patch
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from features.reservations.domain.models.reservation import TableReservation
		
		user1_id = test_data["user"]["id"]
		other_user_id = 999
		table_id = test_data["tables"][0]["id"]
		
		with app.app_context():
			# Create a reservation owned by another user
			repo = SqlAlchemyReservationRepository()
			other_res = TableReservation(
				customer_id=other_user_id,
				table_id=table_id,
				start_ts=datetime(2026, 4, 1, 18, 0),
				end_ts=datetime(2026, 4, 1, 20, 0),
				party_size=4,
			)
			created = repo.add(other_res)
			reservation_id = created.id
			
			# User 1 tries to access it
			user1_logged_in = FakeCurrentUser(user_id=user1_id, is_authenticated=True, is_staff=False)
			
			with app.test_client() as client:
				with patch(
					'features.reservations.presentation.api.reservation_routes.current_user',
					user1_logged_in
				):
					response = client.get(f"/api/reservations/{reservation_id}")
					
					assert response.status_code == 403, (
						f"Non-owner should get 403, got {response.status_code}: {response.get_json()}"
					)
					data = response.get_json()
					assert "Unauthorized" in data.get("error", ""), \
						f"Error should mention authorization, got: {data}"
	
	def test_staff_user_can_see_all_reservations(self, app, test_data):
		"""
		REQUIREMENT: When a staff user GETs /api/reservations, 
		they should see reservations from all customers.
		"""
		from unittest.mock import patch
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from features.reservations.domain.models.reservation import TableReservation
		
		staff_user_id = 99999  # Not the owner of any reservation
		table_id = test_data["tables"][0]["id"]
		
		with app.app_context():
			# Create reservations for multiple users
			repo = SqlAlchemyReservationRepository()
			for customer_id in [1, 2, 3]:
				res = TableReservation(
					customer_id=customer_id,
					table_id=table_id,
					start_ts=datetime(2026, 3, 30, 18, 0) + timedelta(days=customer_id - 1),
					end_ts=datetime(2026, 3, 30, 20, 0) + timedelta(days=customer_id - 1),
					party_size=4,
				)
				repo.add(res)
			
			# Staff user requests all reservations
			staff_logged_in = FakeCurrentUser(user_id=staff_user_id, is_authenticated=True, is_staff=True)
			
			with app.test_client() as client:
				with patch(
					'features.reservations.presentation.api.reservation_routes.current_user',
					staff_logged_in
				):
					response = client.get("/api/reservations")
					assert response.status_code == 200
					data = response.get_json()
					
					# Should contain reservations from all customers
					customer_ids = {r["customer_id"] for r in data}
					assert 1 in customer_ids and 2 in customer_ids and 3 in customer_ids, (
						f"Staff should see all reservations. Got customer_ids: {customer_ids}"
					)
	
	def test_staff_user_can_read_any_reservation(self, app, test_data):
		"""REQUIREMENT: Staff users can GET any reservation details."""
		from unittest.mock import patch
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from features.reservations.domain.models.reservation import TableReservation
		
		staff_user_id = 99999
		customer_id = 123
		table_id = test_data["tables"][0]["id"]
		
		with app.app_context():
			# Create a reservation
			repo = SqlAlchemyReservationRepository()
			res = TableReservation(
				customer_id=customer_id,
				table_id=table_id,
				start_ts=datetime(2026, 4, 5, 18, 0),
				end_ts=datetime(2026, 4, 5, 20, 0),
				party_size=4,
			)
			created = repo.add(res)
			reservation_id = created.id
			
			# Staff user accesses it
			staff_logged_in = FakeCurrentUser(user_id=staff_user_id, is_authenticated=True, is_staff=True)
			
			with app.test_client() as client:
				with patch(
					'features.reservations.presentation.api.reservation_routes.current_user',
					staff_logged_in
				):
					response = client.get(f"/api/reservations/{reservation_id}")
					assert response.status_code == 200, \
						f"Staff should access any reservation, got {response.status_code}"
					data = response.get_json()
					assert data["id"] == reservation_id
