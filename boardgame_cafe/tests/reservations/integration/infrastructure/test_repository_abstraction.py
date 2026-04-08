"""
Repository Abstraction Tests - Integration Tests for Dependency Inversion

These tests enforce the repository pattern and dependency inversion principle:
- Use cases MUST depend on repository interfaces, not concrete implementations
- This ensures replaceable implementations (e.g., swap SQL for in-memory)
"""

import inspect
import pytest


class TestRepositoryDependencyInversion:
	"""Tests ensuring proper dependency inversion in the repository pattern."""
	
	def test_create_reservation_use_case_depends_on_interface_not_implementation(self):
		"""
		REQUIREMENT: CreateReservationUseCase.__init__(repo) must be type-hinted 
		with ReservationRepositoryInterface, not SqlAlchemyReservationRepository.
		
		This allows swapping implementations without changing the use case.
		"""
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationUseCase
		)
		from features.reservations.application.interfaces.reservation_repository_interface import (
			ReservationRepositoryInterface
		)
		
		sig = inspect.signature(CreateReservationUseCase.__init__)
		repo_param = sig.parameters['repo']
		
		# The type hint MUST be the interface
		assert repo_param.annotation == ReservationRepositoryInterface, (
			f"CreateReservationUseCase should depend on ReservationRepositoryInterface, "
			f"but got {repo_param.annotation}"
		)
	
	def test_use_cases_do_not_instantiate_repositories(self):
		"""
		REQUIREMENT: Use case source code MUST NOT contain 'SqlAlchemy' or 'db.session'.
		The use case should receive a pre-configured repository instance.
		
		This is a code smell test to catch violations of dependency injection.
		"""
		from features.reservations.application.use_cases import reservation_use_cases
		
		source = inspect.getsource(reservation_use_cases)
		
		forbidden_patterns = [
			'SqlAlchemy',
			'db.session',
			'TableReservationDB',
			'GameReservationDB',
			'from shared.infrastructure import db',
		]
		
		for pattern in forbidden_patterns:
			assert pattern not in source, (
				f"Use cases should not contain '{pattern}' - this indicates "
				f"pulling in infrastructure directly instead of via dependency injection"
			)
	
	def test_booking_use_case_depends_on_availability_interfaces(self):
		"""
		REQUIREMENT: CreateBookingUseCase must depend on availability repository interfaces.
		This ensures the booking logic can be tested with fake implementations.
		"""
		from features.reservations.application.use_cases.booking_use_cases import (
			CreateBookingUseCase
		)
		from features.reservations.application.interfaces.available_table_repository_interface import (
			AvailableTableRepositoryInterface
		)
		from features.reservations.application.interfaces.available_game_copy_repository_interface import (
			AvailableGameCopyRepositoryInterface
		)
		
		sig = inspect.signature(CreateBookingUseCase.__init__)
		params = sig.parameters
		
		# Check that the use case receives the interfaces, not implementations
		assert 'available_table_repo' in params, \
			"CreateBookingUseCase should have an available_table_repo parameter"
		assert 'available_copy_repo' in params, \
			"CreateBookingUseCase should have an available_copy_repo parameter"
		
		table_repo_hint = params['available_table_repo'].annotation
		copy_repo_hint = params['available_copy_repo'].annotation
		
		assert table_repo_hint == AvailableTableRepositoryInterface, (
			f"available_table_repo should be annotated with "
			f"AvailableTableRepositoryInterface, got {table_repo_hint}"
		)
		assert copy_repo_hint == AvailableGameCopyRepositoryInterface, (
			f"available_copy_repo should be annotated with "
			f"AvailableGameCopyRepositoryInterface, got {copy_repo_hint}"
		)


class TestRepositoryInterfaceCompleteness:
	"""Tests ensuring repository implementations match their interface contracts."""
	
	def test_reservation_repository_implements_all_interface_methods(self):
		"""
		REQUIREMENT: SqlAlchemyReservationRepository must implement ALL methods 
		from ReservationRepositoryInterface.
		"""
		from features.reservations.infrastructure.repositories.reservation_repository import (
			SqlAlchemyReservationRepository
		)
		from features.reservations.application.interfaces.reservation_repository_interface import (
			ReservationRepositoryInterface
		)
		
		# Get all public methods of the interface
		interface_methods = {
			name for name, method in inspect.getmembers(ReservationRepositoryInterface)
			if not name.startswith('_') and callable(method)
		}
		
		# Get all public methods of the implementation
		impl_methods = {
			name for name, method in inspect.getmembers(SqlAlchemyReservationRepository)
			if not name.startswith('_') and callable(method)
		}
		
		# All interface methods must be implemented
		missing = interface_methods - impl_methods
		assert not missing, (
			f"SqlAlchemyReservationRepository is missing these interface methods: {missing}"
		)
	
	def test_available_table_repository_implements_all_interface_methods(self):
		"""Query repository implementations must implement their interface contracts."""
		from features.reservations.infrastructure.repositories.available_table_repository import (
			SqlAlchemyAvailableTableRepository
		)
		from features.reservations.application.interfaces.available_table_repository_interface import (
			AvailableTableRepositoryInterface
		)
		
		interface_methods = {
			name for name, method in inspect.getmembers(AvailableTableRepositoryInterface)
			if not name.startswith('_') and callable(method)
		}
		
		impl_methods = {
			name for name, method in inspect.getmembers(SqlAlchemyAvailableTableRepository)
			if not name.startswith('_') and callable(method)
		}
		
		missing = interface_methods - impl_methods
		assert not missing, (
			f"SqlAlchemyAvailableTableRepository is missing: {missing}"
		)


class TestRepositorySwappability:
	"""Tests demonstrating that use cases work with different repository implementations."""
	
	def test_use_case_works_with_fake_repository(self):
		"""
		DEMONSTRATION: CreateReservationUseCase should work with any 
		ReservationRepositoryInterface implementation, not just SQL.
		"""
		from features.reservations.application.use_cases.reservation_use_cases import (
			CreateReservationUseCase,
			CreateReservationCommand
		)
		from features.reservations.domain.models.reservation import TableReservation
		from datetime import datetime
		
		# Implement a minimal fake that satisfies the interface
		class FakeReservationRepository:
			def __init__(self):
				self.items = []
				self.next_id = 1
			
			def add(self, reservation):
				reservation.id = self.next_id
				self.next_id += 1
				self.items.append(reservation)
				return reservation
			
			def get_by_id(self, res_id):
				return next((r for r in self.items if r.id == res_id), None)
			
			def list_for_table_in_window(self, table_id, start_ts, end_ts):
				return [
					r for r in self.items
					if r.table_id == table_id and r.start_ts < end_ts and start_ts < r.end_ts
				]
			
			def update(self, reservation):
				return reservation
		
		# The use case should work perfectly with this fake
		fake_repo = FakeReservationRepository()
		use_case = CreateReservationUseCase(fake_repo)
		
		cmd = CreateReservationCommand(
			customer_id=1,
			table_id=2,
			start_ts=datetime(2026, 3, 30, 18, 0),
			end_ts=datetime(2026, 3, 30, 20, 0),
			party_size=4,
		)
		
		result = use_case.execute(cmd)
		
		# The use case doesn't know it's using a fake - it just depends on the interface
		assert result.id == 1
		assert result.customer_id == 1
		assert fake_repo.get_by_id(1) is not None
