import inspect
from copy import deepcopy
from dataclasses import replace
from typing import Optional, Sequence

import pytest

from domain.models.table import VALID_TABLE_STATUSES, Table
from application.interfaces.repositories.table_repository import TableFilters, TableRepository


def test_table_repository_cannot_be_instantiated_directly():
	with pytest.raises(TypeError, match="abstract"):
		TableRepository()


def test_table_repository_declares_expected_abstract_methods():
	assert TableRepository.__abstractmethods__ == {
		"add",
		"get_by_id",
		"list",
		"update",
		"delete",
		"search",
		"count_by_status",
	}


def test_table_repository_method_signatures_are_stable():
	signatures = {
		"add": ["self", "table"],
		"get_by_id": ["self", "table_id"],
		"list": ["self"],
		"update": ["self", "table"],
		"delete": ["self", "table_id"],
		"search": ["self", "filters"],
		"count_by_status": ["self"],
	}

	for method_name, expected_params in signatures.items():
		method = getattr(TableRepository, method_name)
		params = list(inspect.signature(method).parameters)
		assert params == expected_params


def test_table_filters_defaults_are_none():
	filters = TableFilters()

	assert filters.zone is None
	assert filters.status is None
	assert filters.min_capacity is None
	assert filters.max_capacity is None
	assert filters.feature is None
	assert filters.is_available is None


def test_table_filters_is_immutable_value_object():
	filters = TableFilters(zone="A")

	with pytest.raises(AttributeError):
		filters.zone = "B"


class InMemoryTableRepository(TableRepository):
	"""Reference implementation used as a behavioral contract for TDD."""

	def __init__(self):
		self._next_id = 1
		self._tables: dict[int, Table] = {}

	def add(self, table: Table) -> Table:
		saved = deepcopy(table)
		setattr(saved, "id", self._next_id)
		self._tables[self._next_id] = saved
		self._next_id += 1
		return deepcopy(saved)

	def get_by_id(self, table_id: int) -> Optional[Table]:
		table = self._tables.get(table_id)
		if table is None:
			return None
		return deepcopy(table)

	def list(self) -> Sequence[Table]:
		return [deepcopy(self._tables[table_id]) for table_id in sorted(self._tables)]

	def update(self, table: Table) -> Table:
		table_id = getattr(table, "id", None)
		if table_id is None:
			raise ValueError("Cannot update table without an id")
		if table_id not in self._tables:
			raise ValueError(f"Table with id {table_id} does not exist")

		self._tables[table_id] = deepcopy(table)
		return deepcopy(self._tables[table_id])

	def delete(self, table_id: int) -> None:
		if table_id not in self._tables:
			raise ValueError(f"Table with id {table_id} does not exist")
		del self._tables[table_id]

	def search(self, filters: Optional[TableFilters] = None) -> Sequence[Table]:
		filters = filters or TableFilters()
		tables = self.list()

		if filters.zone is not None:
			tables = [table for table in tables if table.zone == filters.zone]

		if filters.status is not None:
			tables = [table for table in tables if table.status == filters.status]

		if filters.is_available is not None:
			if filters.is_available:
				tables = [table for table in tables if table.status == "available"]
			else:
				tables = [table for table in tables if table.status != "available"]

		if filters.min_capacity is not None:
			tables = [table for table in tables if table.capacity >= filters.min_capacity]

		if filters.max_capacity is not None:
			tables = [table for table in tables if table.capacity <= filters.max_capacity]

		if filters.feature is not None:
			tables = [
				table
				for table in tables
				if bool((table.features or {}).get(filters.feature))
			]

		return tables

	def count_by_status(self) -> dict[str, int]:
		counts = {status: 0 for status in VALID_TABLE_STATUSES}
		for table in self._tables.values():
			counts[table.status] = counts.get(table.status, 0) + 1
		return counts


@pytest.fixture
def repository() -> InMemoryTableRepository:
	return InMemoryTableRepository()


@pytest.fixture
def seeded_repository(repository: InMemoryTableRepository) -> InMemoryTableRepository:
	for table in [
		Table(number=1, capacity=2, zone="A", features={"near_window": True}, status="available"),
		Table(number=2, capacity=4, zone="A", features={"near_window": False}, status="occupied"),
		Table(number=3, capacity=6, zone="B", features={"near_window": True}, status="available"),
		Table(number=4, capacity=8, zone="B", features={"near_window": False}, status="maintenance"),
		Table(number=5, capacity=4, zone="C", features={"near_window": False}, status="reserved"),
	]:
		repository.add(table)
	return repository


def test_add_get_and_list_roundtrip(repository: InMemoryTableRepository):
	created = repository.add(Table(number=10, capacity=4, zone="Main", features={}, status="available"))

	assert getattr(created, "id", None) is not None
	assert repository.get_by_id(created.id).number == 10
	assert len(repository.list()) == 1


def test_update_requires_existing_id(repository: InMemoryTableRepository):
	with pytest.raises(ValueError, match="without an id"):
		repository.update(Table(number=10, capacity=4, zone="Main", features={}, status="available"))

	ghost = Table(number=11, capacity=4, zone="Main", features={}, status="available")
	setattr(ghost, "id", 999)
	with pytest.raises(ValueError, match="does not exist"):
		repository.update(ghost)


def test_update_persists_changes(seeded_repository: InMemoryTableRepository):
	table = seeded_repository.get_by_id(1)
	updated_input = replace(table, capacity=5, status="reserved")
	setattr(updated_input, "id", table.id)

	updated = seeded_repository.update(updated_input)
	reloaded = seeded_repository.get_by_id(1)

	assert updated.capacity == 5
	assert updated.status == "reserved"
	assert reloaded.capacity == 5
	assert reloaded.status == "reserved"


def test_delete_removes_item_and_missing_delete_raises(repository: InMemoryTableRepository):
	saved = repository.add(Table(number=12, capacity=2, zone="A", features={}, status="available"))
	repository.delete(saved.id)

	assert repository.get_by_id(saved.id) is None
	with pytest.raises(ValueError, match="does not exist"):
		repository.delete(saved.id)


def test_search_supports_filters_and_combination(seeded_repository: InMemoryTableRepository):
	by_zone = seeded_repository.search(TableFilters(zone="B"))
	assert {table.number for table in by_zone} == {3, 4}

	available = seeded_repository.search(TableFilters(is_available=True))
	assert {table.number for table in available} == {1, 3}

	combined = seeded_repository.search(
		TableFilters(zone="B", min_capacity=6, status="available")
	)
	assert {table.number for table in combined} == {3}


def test_count_by_status_includes_all_known_statuses(seeded_repository: InMemoryTableRepository):
	counts = seeded_repository.count_by_status()

	assert set(counts) == VALID_TABLE_STATUSES
	assert counts["available"] == 2
	assert counts["occupied"] == 1
	assert counts["reserved"] == 1
	assert counts["maintenance"] == 1
