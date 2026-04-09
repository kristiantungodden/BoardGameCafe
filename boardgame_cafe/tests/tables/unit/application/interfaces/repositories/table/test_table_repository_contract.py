import inspect

from features.tables.application.interfaces.table_repository import TableFilters, TableRepository


def test_table_repository_cannot_be_instantiated_directly():
	try:
		TableRepository()
		assert False, "Expected TypeError when instantiating abstract class"
	except TypeError as exc:
		assert "abstract" in str(exc).lower()


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

	assert filters.floor is None
	assert filters.zone is None
	assert filters.status is None
	assert filters.min_capacity is None
	assert filters.max_capacity is None
	assert filters.feature is None
	assert filters.is_available is None
