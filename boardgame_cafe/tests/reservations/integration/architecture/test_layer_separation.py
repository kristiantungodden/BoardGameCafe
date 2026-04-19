"""
Architecture Layer Separation Tests - Integration Tests for Clean Architecture

These tests enforce that layers are properly separated:
- Domain layer has NO framework dependencies
- Presentation layer does NOT import infrastructure models
- Application layer uses dependency injection, not service locators
- Each layer only depends on lower layers
"""

import inspect
import pytest


class TestDomainLayerPurity:
	"""Tests ensuring the domain layer has no framework pollution."""
	
	def test_domain_models_do_not_import_flask(self):
		"""
		REQUIREMENT: Domain models MUST NOT import Flask or any other web framework.
		
		Domain logic must be pure business logic, testable without HTTP infrastructure.
		"""
		from features.reservations.domain.models import reservation_game, table_reservation
		
		source = inspect.getsource(reservation_game) + inspect.getsource(table_reservation)
		
		forbidden = [
			"from flask",
			"import flask",
			"from werkzeug",
			"import request",
			"from request",
		]
		
		for pattern in forbidden:
			assert pattern.lower() not in source.lower(), (
				f"Domain model should not import '{pattern}' - "
				f"this couples business logic to web framework"
			)
	
	def test_domain_models_do_not_import_sqlalchemy(self):
		"""
		REQUIREMENT: Domain models MUST NOT import SQLAlchemy or database models.
		
		Domain models represent business concepts, not database tables.
		"""
		from features.reservations.domain.models import reservation_game, table_reservation
		
		source = inspect.getsource(reservation_game) + inspect.getsource(table_reservation)
		
		forbidden = [
			"from sqlalchemy",
			"import sqlalchemy",
			"from sqlalchemy.orm",
			"Column(",
			"String(",
			"Integer(",
			"db.",
			"TableReservationDB",
			"GameReservationDB",
		]
		
		for pattern in forbidden:
			assert pattern not in source, (
				f"Domain model should not contain '{pattern}' - "
				f"this couples business logic to infrastructure"
			)
	
	def test_domain_exceptions_are_framework_agnostic(self):
		"""
		REQUIREMENT: Domain exceptions MUST NOT depend on Flask or framework specifics.
		
		Exceptions should be translatable to any HTTP framework (FastAPI, Django, etc).
		"""
		from shared.domain import exceptions
		
		source = inspect.getsource(exceptions)
		
		# Should not contain Flask-specific things
		assert "flask" not in source.lower()
		assert "abort(" not in source
		assert "werkzeug" not in source.lower()


class TestPresentationLayerBoundaries:
	"""Tests ensuring presentation layer doesn't leak infrastructure."""
	
	def test_api_routes_do_not_import_database_models_directly(self):
		"""
		REQUIREMENT: API routes MUST NOT import database model classes
		(TableReservationDB, GameReservationDB, etc).
		
		Routes should work with domain models and DTOs, not infrastructure models.
		"""
		from features.reservations.presentation.api import reservation_routes
		
		source = inspect.getsource(reservation_routes)
		
		forbidden_db_imports = [
			"TableReservationDB",
			"GameReservationDB",
			"UserDB",
			"TableDB",
			"GameDB",
			"from features.reservations.infrastructure.database",
			"from features.tables.infrastructure.database",
			"from features.games.infrastructure.database",
			".infrastructure.database",
		]
		
		for pattern in forbidden_db_imports:
			assert pattern not in source, (
				f"API routes should not import '{pattern}' - "
				f"this couples presentation to infrastructure"
			)
	
	def test_api_routes_do_not_import_use_cases_directly(self):
		"""
		REQUIREMENT: API routes MUST receive use cases via dependency injection,
		not import them directly.
		
		This allows swapping use case implementations and makes testing easier.
		"""
		from features.reservations.presentation.api import reservation_routes
		
		source = inspect.getsource(reservation_routes)
		
		# Should NOT have direct imports of use case classes
		# (it's ok to have them passed in as dependencies)
		
		# SMELL: Direct instantiation of use case in routes
		assert "CreateReservationUseCase()" not in source, (
			"Routes should not instantiate use cases directly - use DI container"
		)
		assert "CreateBookingUseCase()" not in source, (
			"Routes should not instantiate use cases directly - use DI container"
		)


class TestApplicationLayerDependencyInjection:
	"""Tests ensuring application layer uses proper dependency injection."""
	
	def test_use_cases_receive_dependencies_not_import_them(self):
		"""
		REQUIREMENT: Use cases MUST receive all external dependencies
		through their __init__ method, never import infrastructure directly.
		"""
		from features.reservations.application.use_cases import reservation_use_cases
		
		source = inspect.getsource(reservation_use_cases)
		
		# Should not have direct infrastructure imports
		forbidden = [
			"from shared.infrastructure import db",
			"from ..infrastructure import",
			"db.session",
			"TableReservationDB",
		]
		
		for pattern in forbidden:
			assert pattern not in source, (
				f"Use cases should not import '{pattern}' directly - "
				f"receive as constructor parameter instead"
			)
	
	def test_dependency_injection_container_has_minimal_logic(self):
		"""
		REQUIREMENT: DI containers should ONLY wire up components.
		It should NOT contain business logic, conditionals, or queries.
		"""
		from features.reservations.composition import reservation_use_case_factories as reservation_deps
		from features.tables.composition import table_use_case_factories as table_deps

		for module in (reservation_deps, table_deps):
			source = inspect.getsource(module)

			# Allow factory functions like `def get_xxx_handler():`
			# But discourage business logic and data access
			assert ".query(" not in source, (
				"Dependency injection should not perform database queries"
			)
			assert "session.query" not in source, (
				"Dependency injection should not perform database queries"
			)
			assert "session.execute" not in source, (
				"Dependency injection should not perform database queries"
			)


class TestLayerImportHierarchy:
	"""Tests ensuring correct dependency direction between layers."""
	
	def test_presentation_only_imports_application_not_infrastructure(self):
		"""
		REQUIREMENT: Presentation layer can only import from:
		- Application (use cases, interfaces)
		- Shared domain (exceptions, models)
		
		Must NOT import from Infrastructure directly.
		"""
		# This is enforced by test_api_routes_do_not_import_database_models_directly
		# Documenting the principle here
		pass
	
	def test_application_only_imports_domain_and_repositories_not_presentation(self):
		"""
		REQUIREMENT: Application layer can only import from:
		- Domain (models, exceptions)
		- Repository interfaces (not implementations)
		
		Must NOT import from Presentation or specific infrastructure implementations.
		"""
		from features.reservations.application.use_cases import reservation_use_cases
		
		source = inspect.getsource(reservation_use_cases)
		
		forbidden_imports = [
			"from features.reservations.presentation",
			"from features.reservations.infrastructure.database",
		]
		
		for pattern in forbidden_imports:
			assert pattern not in source, (
				f"Use cases should not import '{pattern}' - "
				f"violates dependency direction"
			)
	
	def test_infrastructure_can_import_domain_and_shared_not_presentation(self):
		"""
		REQUIREMENT: Infrastructure implementations can only import from:
		- Domain (models, exceptions)
		- Shared infrastructure
		
		Must NOT import from Presentation or Application logic.
		"""
		from features.reservations.infrastructure.repositories import reservation_repository
		
		source = inspect.getsource(reservation_repository)
		
		forbidden_imports = [
			"from features.reservations.presentation",
			"from features.reservations.application.use_cases",
		]
		
		for pattern in forbidden_imports:
			assert pattern not in source, (
				f"Infrastructure should not import '{pattern}' - "
				f"violates layer isolation"
			)


class TestNoCircularDependencies:
	"""Tests ensuring no circular dependencies between layers."""
	
	def test_no_circular_imports_between_layers(self):
		"""
		REQUIREMENT: No layer should import from a layer that imports from it.
		
		Valid direction: Domain <- Application <- Presentation
		                 Domain <- Infrastructure
		
		Invalid: Application importing from Presentation,
		         Presentation importing from Infrastructure implementations
		"""
		# This is implicitly tested by:
		# - test_presentation_only_imports_application_not_infrastructure
		# - test_application_only_imports_domain_and_repositories_not_presentation
		# - test_infrastructure_can_import_domain_and_shared_not_presentation
		
		# Documenting the principle here
		pass
