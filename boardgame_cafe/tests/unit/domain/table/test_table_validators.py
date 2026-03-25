from domain.models.table.table import Table, VALID_TABLE_STATUSES
from domain.exceptions import ValidationError, InvalidStatusTransition

def test_table_validators():
    # Test valid table creation
    table = Table(number=1, capacity=4)
    assert table.number == 1
    assert table.capacity == 4
    assert table.status == VALID_TABLE_STATUSES.intersection({"available"})

    # Test invalid number
    try:
        Table(number=0, capacity=4)
        assert False, "Expected ValidationError for number <= 0"
    except ValidationError as e:
        assert str(e) == "number must be a positive integer"

    # Test invalid capacity
    try:
        Table(number=1, capacity=0)
        assert False, "Expected ValidationError for capacity <= 0"
    except ValidationError as e:
        assert str(e) == "capacity must be a positive integer"

    # Test invalid status
    try:
        Table(number=1, capacity=4, status="invalid")
        assert False, "Expected ValidationError for invalid status"
    except ValidationError as e:
        expected_statuses = ", ".join(sorted(VALID_TABLE_STATUSES))
        assert str(e) == f"status must be one of: {expected_statuses}"