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


def test_start_maintenance_from_available_sets_maintenance():
    table = Table(number=8, capacity=4, status="available")
    table.start_maintenance()
    assert table.status == "maintenance"


def test_start_maintenance_from_reserved_raises():
    table = Table(number=9, capacity=4, status="reserved")
    with pytest.raises(InvalidStatusTransition, match="Cannot start maintenance"):
        table.start_maintenance()


def test_finish_maintenance_sets_available():
    table = Table(number=10, capacity=4, status="maintenance")
    table.finish_maintenance()
    assert table.status == "available"


def test_finish_maintenance_from_non_maintenance_raises():
    table = Table(number=11, capacity=4, status="available")
    with pytest.raises(InvalidStatusTransition, match="Cannot finish maintenance"):
        table.finish_maintenance()


def test_reserve_from_maintenance_raises():
    table = Table(number=12, capacity=4, status="maintenance")
    with pytest.raises(InvalidStatusTransition, match="Cannot reserve table"):
        table.reserve()


def test_occupy_from_maintenance_raises():
    table = Table(number=13, capacity=4, status="maintenance")
    with pytest.raises(InvalidStatusTransition, match="Cannot occupy table"):
        table.occupy()


def test_free_from_maintenance_raises():
    table = Table(number=14, capacity=4, status="maintenance")
    with pytest.raises(InvalidStatusTransition, match="Cannot free table"):
        table.free()
