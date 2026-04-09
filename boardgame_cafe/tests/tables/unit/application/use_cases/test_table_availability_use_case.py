from datetime import datetime

from features.bookings.domain.models.booking import Booking
from features.tables.application.use_cases.table_availability_use_case import (
    GetTableAvailabilityUseCase,
)
from features.tables.domain.models.table import Table


def _make_reservation(*, table_id: int, **kwargs) -> Booking:
    reservation = Booking(**kwargs)
    setattr(reservation, "table_id", table_id)
    return reservation


class FakeTableRepository:
    def __init__(self, tables):
        self.tables = tables

    def search(self, filters=None):
        tables = list(self.tables)
        if filters and filters.floor is not None:
            tables = [table for table in tables if table.floor == filters.floor]
        return tables


class FakeReservationRepository:
    def __init__(self, reservations):
        self.reservations = reservations

    def list_for_table_in_window(self, table_id: int, start_ts: datetime, end_ts: datetime):
        return [
            reservation
            for reservation in self.reservations
            if reservation.table_id == table_id
            and reservation.start_ts < end_ts
            and start_ts < reservation.end_ts
        ]


def test_table_availability_groups_by_floor_and_zone_and_marks_blocked_tables():
    start_ts = datetime(2026, 4, 10, 18, 0)
    end_ts = datetime(2026, 4, 10, 20, 0)

    tables = [
        Table(number=1, capacity=4, floor=1, zone="A", status="available"),
        Table(number=2, capacity=2, floor=1, zone="A", status="available"),
        Table(number=3, capacity=6, floor=2, zone="B", status="occupied"),
        Table(number=4, capacity=6, floor=2, zone="C", status="available"),
    ]
    for idx, table in enumerate(tables, start=1):
        setattr(table, "id", idx)

    reservations = [
        _make_reservation(
            id=99,
            customer_id=1,
            table_id=4,
            start_ts=datetime(2026, 4, 10, 19, 0),
            end_ts=datetime(2026, 4, 10, 21, 0),
            party_size=4,
            status="confirmed",
        )
    ]

    use_case = GetTableAvailabilityUseCase(
        table_repo=FakeTableRepository(tables),
        reservation_repo=FakeReservationRepository(reservations),
    )

    result = use_case.execute(start_ts, end_ts, party_size=4)

    assert result["filters"]["party_size"] == 4
    assert [floor["floor"] for floor in result["floors"]] == [1, 2]

    floor_one = result["floors"][0]
    assert floor_one["zones"][0]["zone"] == "A"

    table_one, table_two = floor_one["zones"][0]["tables"]
    assert table_one["available"] is True
    assert table_one["unavailable_reasons"] == []
    assert table_two["available"] is False
    assert "capacity" in table_two["unavailable_reasons"]

    floor_two = result["floors"][1]
    zone_names = [zone["zone"] for zone in floor_two["zones"]]
    assert zone_names == ["B", "C"]

    occupied_table = floor_two["zones"][0]["tables"][0]
    blocked_table = floor_two["zones"][1]["tables"][0]

    assert occupied_table["available"] is False
    assert "table_status" in occupied_table["unavailable_reasons"]
    assert blocked_table["available"] is False
    assert "reservation_overlap" in blocked_table["unavailable_reasons"]


def test_table_availability_filters_to_requested_floor():
    start_ts = datetime(2026, 4, 10, 18, 0)
    end_ts = datetime(2026, 4, 10, 20, 0)

    tables = [
        Table(number=1, capacity=4, floor=1, zone="A", status="available"),
        Table(number=2, capacity=4, floor=2, zone="B", status="available"),
    ]
    for idx, table in enumerate(tables, start=1):
        setattr(table, "id", idx)

    use_case = GetTableAvailabilityUseCase(
        table_repo=FakeTableRepository(tables),
        reservation_repo=FakeReservationRepository([]),
    )

    result = use_case.execute(start_ts, end_ts, party_size=4, floor=2)

    assert [floor["floor"] for floor in result["floors"]] == [2]
    assert result["floors"][0]["zones"][0]["tables"][0]["table_nr"] == "2"