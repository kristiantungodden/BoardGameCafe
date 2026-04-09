import pytest

from shared.domain.exceptions import ValidationError
from features.tables.domain.models.table import Table, VALID_TABLE_STATUSES


def test_table_creation_uses_expected_defaults():
    table = Table(number=1, capacity=4)

    assert table.number == 1
    assert table.capacity == 4
    assert table.floor == 1
    assert table.status == "available"


def test_table_number_must_be_positive():
    with pytest.raises(ValidationError, match="number must be a positive integer"):
        Table(number=0, capacity=4)


def test_table_capacity_must_be_positive():
    with pytest.raises(ValidationError, match="capacity must be a positive integer"):
        Table(number=1, capacity=0)


def test_table_floor_must_be_positive():
    with pytest.raises(ValidationError, match="floor must be a positive integer"):
        Table(number=1, capacity=4, floor=0)


def test_table_status_must_be_known_value():
    with pytest.raises(ValidationError) as exc_info:
        Table(number=1, capacity=4, status="abcd")

    expected_statuses = ", ".join(sorted(VALID_TABLE_STATUSES))
    assert str(exc_info.value) == f"status must be one of: {expected_statuses}"