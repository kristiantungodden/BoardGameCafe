import pytest

from domain.exceptions import InvalidStatusTransition
from domain.models.table import Table


def test_reserve_from_available_sets_reserved():
    table = Table(number=1, capacity=4, status="available")

    table.reserve()

    assert table.status == "reserved"


def test_reserve_from_non_available_raises():
    table = Table(number=1, capacity=4, status="occupied")

    with pytest.raises(InvalidStatusTransition, match="Cannot reserve table"):
        table.reserve()


def test_occupy_from_available_sets_occupied():
    table = Table(number=2, capacity=4, status="available")

    table.occupy()

    assert table.status == "occupied"


def test_occupy_from_reserved_sets_occupied():
    table = Table(number=3, capacity=6, status="reserved")

    table.occupy()

    assert table.status == "occupied"


def test_occupy_from_occupied_raises():
    table = Table(number=4, capacity=2, status="occupied")

    with pytest.raises(InvalidStatusTransition, match="Cannot occupy table"):
        table.occupy()


def test_free_from_occupied_sets_available():
    table = Table(number=5, capacity=2, status="occupied")

    table.free()

    assert table.status == "available"


def test_free_from_reserved_sets_available():
    table = Table(number=6, capacity=2, status="reserved")

    table.free()

    assert table.status == "available"


def test_free_from_available_raises():
    table = Table(number=7, capacity=4, status="available")

    with pytest.raises(InvalidStatusTransition, match="Cannot free table"):
        table.free()
