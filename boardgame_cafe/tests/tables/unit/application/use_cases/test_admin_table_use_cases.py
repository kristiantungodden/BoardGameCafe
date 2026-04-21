from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from features.bookings.domain.models.booking import Booking
from features.tables.application.interfaces.table_repository import TableFilters
from features.tables.application.use_cases.admin_table_use_cases import (
    CreateZoneCommand,
    CreateFloorCommand,
    CreateTableCommand,
    CreateZoneUseCase,
    DeleteZoneUseCase,
    DeleteFloorUseCase,
    DeleteTableUseCase,
    UpdateFloorCommand,
    UpdateTableCommand,
    UpdateZoneCommand,
    CreateFloorUseCase,
    CreateTableUseCase,
    UpdateFloorUseCase,
    UpdateTableUseCase,
    UpdateZoneUseCase,
)
from features.tables.domain.models.floor import Floor
from features.tables.domain.models.table import Table
from shared.domain.exceptions import ValidationError


class FakeFloorRepo:
    def __init__(self):
        self.items = {}
        self.next_id = 1

    def add(self, floor):
        floor.id = self.next_id
        self.next_id += 1
        self.items[floor.id] = floor
        return floor

    def get_by_id(self, floor_id):
        return self.items.get(floor_id)

    def get_by_number(self, floor_number):
        for floor in self.items.values():
            if floor.number == floor_number:
                return floor
        return None

    def list(self):
        return list(self.items.values())

    def update(self, floor):
        self.items[floor.id] = floor
        return floor

    def delete(self, floor_id):
        self.items.pop(floor_id, None)


class FakeTableRepo:
    def __init__(self):
        self.items = {}
        self.next_id = 1

    def add(self, table):
        table.id = self.next_id
        self.next_id += 1
        self.items[table.id] = table
        return table

    def get_by_id(self, table_id):
        return self.items.get(table_id)

    def get_by_number(self, number):
        for table in self.items.values():
            if table.number == number:
                return table
        return None

    def list(self):
        return list(self.items.values())

    def update(self, table):
        self.items[table.id] = table
        return table

    def delete(self, table_id):
        self.items.pop(table_id, None)

    def search(self, filters=None):
        tables = list(self.items.values())
        if filters and filters.floor is not None:
            tables = [table for table in tables if table.floor == filters.floor]
        if filters and filters.zone is not None:
            tables = [table for table in tables if table.zone == filters.zone]
        if filters and filters.status is not None:
            tables = [table for table in tables if table.status == filters.status]
        return tables


class FakeZoneRepo:
    def __init__(self):
        self.items = {}
        self.next_id = 1

    def add(self, zone):
        zone.id = self.next_id
        self.next_id += 1
        self.items[zone.id] = zone
        return zone

    def get_by_id(self, zone_id):
        return self.items.get(zone_id)

    def get_by_floor_and_name(self, floor, name):
        for zone in self.items.values():
            if zone.floor == floor and zone.name == name:
                return zone
        return None

    def list(self, floor=None):
        zones = list(self.items.values())
        if floor is not None:
            zones = [zone for zone in zones if zone.floor == floor]
        return zones

    def update(self, zone):
        self.items[zone.id] = zone
        return zone

    def delete(self, zone_id):
        self.items.pop(zone_id, None)


class FakeReservationRepo:
    def __init__(self, reservations):
        self.reservations = reservations

    def list_for_table_in_window(self, table_id, start_ts, end_ts):
        return [reservation for reservation in self.reservations if getattr(reservation, "table_id", None) == table_id and reservation.start_ts < end_ts and start_ts < reservation.end_ts]


def test_create_floor_and_table_use_cases():
    floor_repo = FakeFloorRepo()
    table_repo = FakeTableRepo()
    zone_repo = FakeZoneRepo()

    created_floor = CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Ground floor"))
    assert created_floor.id == 1
    assert created_floor.number == 1
    CreateZoneUseCase(floor_repo, zone_repo).execute(CreateZoneCommand(floor=1, name="A"))

    created_table = CreateTableUseCase(table_repo, floor_repo, zone_repo).execute(
        CreateTableCommand(number=10, capacity=4, floor=1, zone="A")
    )
    assert created_table.id == 1
    assert created_table.floor == 1
    assert created_table.zone == "A"


def test_create_floor_rejects_duplicate_number():
    floor_repo = FakeFloorRepo()
    CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Ground floor"))

    with pytest.raises(ValidationError, match="floor number already exists"):
        CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Second ground floor"))


def test_update_floor_rejects_duplicate_number():
    floor_repo = FakeFloorRepo()
    floor_one = CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Ground floor"))
    CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=2, name="Upper floor"))

    with pytest.raises(ValidationError, match="floor number already exists"):
        UpdateFloorUseCase(floor_repo).execute(
            UpdateFloorCommand(floor_id=floor_one.id, number=2, name="Ground floor updated")
        )


def test_delete_floor_rejects_tables():
    floor_repo = FakeFloorRepo()
    table_repo = FakeTableRepo()
    floor = CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Ground floor"))
    table_repo.add(Table(number=1, capacity=4, floor=1, zone="A"))

    with pytest.raises(ValidationError, match="Cannot delete floor with tables assigned to it"):
        DeleteFloorUseCase(floor_repo, table_repo).execute(floor.id)


def test_update_table_rejects_capacity_reduction_with_future_reservations():
    floor_repo = FakeFloorRepo()
    table_repo = FakeTableRepo()
    zone_repo = FakeZoneRepo()
    floor_repo.add(Floor(number=1, name="Ground floor"))
    CreateZoneUseCase(floor_repo, zone_repo).execute(CreateZoneCommand(floor=1, name="A"))
    table = table_repo.add(Table(number=1, capacity=6, floor=1, zone="A"))
    future_reservation = Booking(
        id=1,
        customer_id=1,
        start_ts=datetime.utcnow() + timedelta(days=1),
        end_ts=datetime.utcnow() + timedelta(days=1, hours=2),
        party_size=4,
        status="confirmed",
        notes=None,
    )
    setattr(future_reservation, "table_id", table.id)

    with pytest.raises(ValidationError, match="Cannot reduce capacity while future reservations exist"):
        UpdateTableUseCase(table_repo, floor_repo, zone_repo, FakeReservationRepo([future_reservation])).execute(
            UpdateTableCommand(
                table_id=table.id,
                number=1,
                capacity=4,
                floor=1,
                zone="A",
            )
        )


def test_delete_table_rejects_future_reservations():
    floor_repo = FakeFloorRepo()
    table_repo = FakeTableRepo()
    floor_repo.add(Floor(number=1, name="Ground floor"))
    table = table_repo.add(Table(number=1, capacity=4, floor=1, zone="A"))
    future_reservation = Booking(
        id=1,
        customer_id=1,
        start_ts=datetime.utcnow() + timedelta(days=1),
        end_ts=datetime.utcnow() + timedelta(days=1, hours=2),
        party_size=4,
        status="confirmed",
        notes=None,
    )
    setattr(future_reservation, "table_id", table.id)

    with pytest.raises(ValidationError, match="Cannot delete table with future reservations"):
        DeleteTableUseCase(table_repo, FakeReservationRepo([future_reservation])).execute(table.id)


def test_create_table_rejects_missing_zone():
    floor_repo = FakeFloorRepo()
    table_repo = FakeTableRepo()
    zone_repo = FakeZoneRepo()
    CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Ground floor"))

    with pytest.raises(ValidationError, match="Zone not found for selected floor"):
        CreateTableUseCase(table_repo, floor_repo, zone_repo).execute(
            CreateTableCommand(number=10, capacity=4, floor=1, zone="Unknown")
        )


def test_delete_zone_rejects_tables_assigned():
    floor_repo = FakeFloorRepo()
    table_repo = FakeTableRepo()
    zone_repo = FakeZoneRepo()

    CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Ground floor"))
    zone = CreateZoneUseCase(floor_repo, zone_repo).execute(CreateZoneCommand(floor=1, name="A"))
    table_repo.add(Table(number=1, capacity=4, floor=1, zone="A"))

    with pytest.raises(ValidationError, match="Cannot delete zone with tables assigned to it"):
        DeleteZoneUseCase(zone_repo, table_repo).execute(zone.id)


def test_update_zone_renames_assigned_tables():
    floor_repo = FakeFloorRepo()
    table_repo = FakeTableRepo()
    zone_repo = FakeZoneRepo()

    CreateFloorUseCase(floor_repo).execute(CreateFloorCommand(number=1, name="Ground floor"))
    zone = CreateZoneUseCase(floor_repo, zone_repo).execute(CreateZoneCommand(floor=1, name="A"))
    table = table_repo.add(Table(number=1, capacity=4, floor=1, zone="A"))

    updated = UpdateZoneUseCase(floor_repo, zone_repo, table_repo).execute(
        UpdateZoneCommand(zone_id=zone.id, floor=1, name="Window")
    )

    assert updated.name == "Window"
    assert table_repo.get_by_id(table.id).zone == "Window"