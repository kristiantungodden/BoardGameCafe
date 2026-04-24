from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from features.reservations.application.interfaces.reservation_repository_interface import ReservationRepositoryInterface
from features.reservations.application.interfaces.table_reservation_repository_interface import (
    TableReservationRepositoryInterface,
)
from features.tables.application.interfaces.floor_repository import FloorRepository
from features.tables.application.interfaces.table_repository import TableRepository, TableFilters
from features.tables.application.interfaces.zone_repository import ZoneRepository
from features.tables.domain.models.floor import Floor
from features.tables.domain.models.table import Table
from features.tables.domain.models.zone import Zone
from shared.domain.exceptions import ValidationError


_MOVE_LOCKED_TABLE_STATUSES = {"occupied"}
_EDIT_DELETE_LOCKED_TABLE_STATUSES = {"occupied"}


@dataclass
class CreateFloorCommand:
    number: int
    name: str
    active: bool = True
    notes: Optional[str] = None


@dataclass
class UpdateFloorCommand:
    floor_id: int
    number: int
    name: str
    active: bool = True
    notes: Optional[str] = None


@dataclass
class CreateTableCommand:
    number: int
    capacity: int
    floor: int
    zone: str
    status: str = "available"
    features: Optional[dict[str, bool]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    rotation: Optional[int] = None


@dataclass
class CreateZoneCommand:
    floor: int
    name: str
    active: bool = True
    notes: Optional[str] = None


@dataclass
class UpdateZoneCommand:
    zone_id: int
    floor: int
    name: str
    active: bool = True
    notes: Optional[str] = None


@dataclass
class UpdateTableCommand:
    table_id: int
    number: int
    capacity: int
    floor: int
    zone: str
    status: str = "available"
    features: Optional[dict[str, bool]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    rotation: Optional[int] = None


class ListFloorsUseCase:
    def __init__(self, floor_repo: FloorRepository):
        self.floor_repo = floor_repo

    def execute(self) -> list[Floor]:
        return list(self.floor_repo.list())


class CreateFloorUseCase:
    def __init__(self, floor_repo: FloorRepository):
        self.floor_repo = floor_repo

    def execute(self, cmd: CreateFloorCommand) -> Floor:
        if self.floor_repo.get_by_number(cmd.number):
            raise ValidationError("floor number already exists")
        return self.floor_repo.add(
            Floor(
                number=cmd.number,
                name=cmd.name,
                active=cmd.active,
                notes=cmd.notes,
            )
        )


class UpdateFloorUseCase:
    def __init__(self, floor_repo: FloorRepository):
        self.floor_repo = floor_repo

    def execute(self, cmd: UpdateFloorCommand) -> Floor:
        existing = self.floor_repo.get_by_id(cmd.floor_id)
        if existing is None:
            raise ValidationError("Floor not found")
        duplicate = self.floor_repo.get_by_number(cmd.number)
        if duplicate is not None and getattr(duplicate, "id", None) != cmd.floor_id:
            raise ValidationError("floor number already exists")
        existing.number = cmd.number
        existing.name = cmd.name
        existing.active = cmd.active
        existing.notes = cmd.notes
        return self.floor_repo.update(existing)


class DeleteFloorUseCase:
    def __init__(self, floor_repo: FloorRepository, table_repo: TableRepository):
        self.floor_repo = floor_repo
        self.table_repo = table_repo

    def execute(self, floor_id: int) -> None:
        floor = self.floor_repo.get_by_id(floor_id)
        if floor is None:
            raise ValidationError("Floor not found")

        tables = self.table_repo.search(TableFilters(floor=floor.number))
        if tables:
            raise ValidationError("Cannot delete floor with tables assigned to it")

        self.floor_repo.delete(floor_id)


class ListTablesUseCase:
    def __init__(self, table_repo: TableRepository):
        self.table_repo = table_repo

    def execute(self, floor: Optional[int] = None) -> list[Table]:
        return list(self.table_repo.search(TableFilters(floor=floor)))


class CreateTableUseCase:
    def __init__(self, table_repo: TableRepository, floor_repo: FloorRepository, zone_repo: ZoneRepository):
        self.table_repo = table_repo
        self.floor_repo = floor_repo
        self.zone_repo = zone_repo

    def execute(self, cmd: CreateTableCommand) -> Table:
        if self.floor_repo.get_by_number(cmd.floor) is None:
            raise ValidationError("Floor not found")
        if self.zone_repo.get_by_floor_and_name(cmd.floor, cmd.zone) is None:
            raise ValidationError("Zone not found for selected floor")
        if self.table_repo.get_by_number(cmd.number) is not None:
            raise ValidationError("table number already exists")

        return self.table_repo.add(
            Table(
                number=cmd.number,
                capacity=cmd.capacity,
                floor=cmd.floor,
                zone=cmd.zone,
                status=cmd.status,
                features=cmd.features or {},
                width=cmd.width,
                height=cmd.height,
                rotation=cmd.rotation,
            )
        )


class UpdateTableUseCase:
    def __init__(
        self,
        table_repo: TableRepository,
        floor_repo: FloorRepository,
        zone_repo: ZoneRepository,
        reservation_repo: ReservationRepositoryInterface,
    ):
        self.table_repo = table_repo
        self.floor_repo = floor_repo
        self.zone_repo = zone_repo
        self.reservation_repo = reservation_repo

    def execute(self, cmd: UpdateTableCommand) -> Table:
        existing = self.table_repo.get_by_id(cmd.table_id)
        if existing is None:
            raise ValidationError("Table not found")
        _ensure_table_is_editable_or_deletable(existing)
        _ensure_table_is_not_moved_while_locked(existing, cmd.floor, cmd.zone)
        if self.floor_repo.get_by_number(cmd.floor) is None:
            raise ValidationError("Floor not found")
        if self.zone_repo.get_by_floor_and_name(cmd.floor, cmd.zone) is None:
            raise ValidationError("Zone not found for selected floor")
        duplicate = self.table_repo.get_by_number(cmd.number)
        if duplicate is not None and getattr(duplicate, "id", None) != cmd.table_id:
            raise ValidationError("table number already exists")

        future_bookings = self.reservation_repo.list_for_table_in_window(
            cmd.table_id,
            datetime.utcnow(),
            datetime.max,
        )
        if future_bookings and cmd.capacity < existing.capacity:
            raise ValidationError("Cannot reduce capacity while future reservations exist")

        existing.number = cmd.number
        existing.capacity = cmd.capacity
        existing.floor = cmd.floor
        existing.zone = cmd.zone
        _apply_table_status_update(existing, cmd.status)
        existing.features = cmd.features or {}
        existing.width = cmd.width
        existing.height = cmd.height
        existing.rotation = cmd.rotation
        return self.table_repo.update(existing)


class DeleteTableUseCase:
    def __init__(
        self,
        table_repo: TableRepository,
        reservation_repo: ReservationRepositoryInterface,
        table_reservation_repo: TableReservationRepositoryInterface,
    ):
        self.table_repo = table_repo
        self.reservation_repo = reservation_repo
        self.table_reservation_repo = table_reservation_repo

    def execute(self, table_id: int) -> None:
        table = self.table_repo.get_by_id(table_id)
        if table is None:
            raise ValidationError("Table not found")
        _ensure_table_is_editable_or_deletable(table)

        future_bookings = self.reservation_repo.list_for_table_in_window(
            table_id,
            datetime.utcnow(),
            datetime.max,
        )
        if future_bookings:
            raise ValidationError("Cannot delete table with future reservations")

        if table.status == "available":
            links = self.table_reservation_repo.list_by_table_id(table_id)
            for link in links:
                if getattr(link, "id", None) is not None:
                    self.table_reservation_repo.delete(link.id)

        self.table_repo.delete(table_id)


class ForceDeleteTableUseCase:
    def __init__(
        self,
        table_repo: TableRepository,
        table_reservation_repo: TableReservationRepositoryInterface,
    ):
        self.table_repo = table_repo
        self.table_reservation_repo = table_reservation_repo

    def execute(self, table_id: int) -> None:
        table = self.table_repo.get_by_id(table_id)
        if table is None:
            raise ValidationError("Table not found")
        _ensure_table_is_editable_or_deletable(table)

        links = self.table_reservation_repo.list_by_table_id(table_id)
        for link in links:
            if getattr(link, "id", None) is not None:
                self.table_reservation_repo.delete(link.id)

        self.table_repo.delete(table_id)


class ListZonesUseCase:
    def __init__(self, zone_repo: ZoneRepository):
        self.zone_repo = zone_repo

    def execute(self, floor: Optional[int] = None) -> list[Zone]:
        return list(self.zone_repo.list(floor=floor))


class CreateZoneUseCase:
    def __init__(self, floor_repo: FloorRepository, zone_repo: ZoneRepository):
        self.floor_repo = floor_repo
        self.zone_repo = zone_repo

    def execute(self, cmd: CreateZoneCommand) -> Zone:
        if self.floor_repo.get_by_number(cmd.floor) is None:
            raise ValidationError("Floor not found")
        if self.zone_repo.get_by_floor_and_name(cmd.floor, cmd.name) is not None:
            raise ValidationError("zone name already exists on this floor")
        return self.zone_repo.add(
            Zone(
                floor=cmd.floor,
                name=cmd.name,
                active=cmd.active,
                notes=cmd.notes,
            )
        )


class UpdateZoneUseCase:
    def __init__(
        self,
        floor_repo: FloorRepository,
        zone_repo: ZoneRepository,
        table_repo: TableRepository,
    ):
        self.floor_repo = floor_repo
        self.zone_repo = zone_repo
        self.table_repo = table_repo

    def execute(self, cmd: UpdateZoneCommand) -> Zone:
        existing = self.zone_repo.get_by_id(cmd.zone_id)
        if existing is None:
            raise ValidationError("Zone not found")
        if self.floor_repo.get_by_number(cmd.floor) is None:
            raise ValidationError("Floor not found")

        duplicate = self.zone_repo.get_by_floor_and_name(cmd.floor, cmd.name)
        if duplicate is not None and getattr(duplicate, "id", None) != cmd.zone_id:
            raise ValidationError("zone name already exists on this floor")

        assigned_tables = self.table_repo.search(
            TableFilters(floor=existing.floor, zone=existing.name)
        )
        if assigned_tables and cmd.floor != existing.floor:
            raise ValidationError(
                "Cannot move zone to another floor while tables are assigned"
            )

        old_name = existing.name
        existing.floor = cmd.floor
        existing.name = cmd.name
        existing.active = cmd.active
        existing.notes = cmd.notes
        updated = self.zone_repo.update(existing)

        if assigned_tables and old_name != updated.name:
            for table in assigned_tables:
                table.zone = updated.name
                self.table_repo.update(table)

        return updated


class DeleteZoneUseCase:
    def __init__(self, zone_repo: ZoneRepository, table_repo: TableRepository):
        self.zone_repo = zone_repo
        self.table_repo = table_repo

    def execute(self, zone_id: int) -> None:
        zone = self.zone_repo.get_by_id(zone_id)
        if zone is None:
            raise ValidationError("Zone not found")

        assigned_tables = self.table_repo.search(TableFilters(floor=zone.floor, zone=zone.name))
        if assigned_tables:
            raise ValidationError("Cannot delete zone with tables assigned to it")

        self.zone_repo.delete(zone_id)


def _ensure_table_is_editable_or_deletable(table: Table) -> None:
    if table.status in _EDIT_DELETE_LOCKED_TABLE_STATUSES:
        raise ValidationError("Cannot edit or delete a table while it is occupied")


def _ensure_table_is_not_moved_while_locked(table: Table, target_floor: int, target_zone: str) -> None:
    if table.status not in _MOVE_LOCKED_TABLE_STATUSES:
        return

    normalized_target_zone = str(target_zone or "").strip()
    normalized_existing_zone = str(table.zone or "").strip()
    if int(table.floor) != int(target_floor) or normalized_existing_zone != normalized_target_zone:
        raise ValidationError("Cannot move a table while it is occupied")


def _apply_table_status_update(table: Table, next_status: str) -> None:
    normalized_next_status = str(next_status or "").strip().lower()
    if normalized_next_status == table.status:
        return

    if table.status == "available" and normalized_next_status == "maintenance":
        table.start_maintenance()
        return

    if table.status == "maintenance" and normalized_next_status == "available":
        table.finish_maintenance()
        return

    table.status = normalized_next_status


class ForceDeleteZoneUseCase:
    def __init__(
        self,
        zone_repo: ZoneRepository,
        table_repo: TableRepository,
        force_delete_table_use_case: ForceDeleteTableUseCase,
    ):
        self.zone_repo = zone_repo
        self.table_repo = table_repo
        self.force_delete_table_use_case = force_delete_table_use_case

    def execute(self, zone_id: int) -> None:
        zone = self.zone_repo.get_by_id(zone_id)
        if zone is None:
            raise ValidationError("Zone not found")

        assigned_tables = self.table_repo.search(TableFilters(floor=zone.floor, zone=zone.name))
        for table in assigned_tables:
            self.force_delete_table_use_case.execute(table.id)

        self.zone_repo.delete(zone_id)


class ForceDeleteFloorUseCase:
    def __init__(
        self,
        floor_repo: FloorRepository,
        zone_repo: ZoneRepository,
        table_repo: TableRepository,
        force_delete_table_use_case: ForceDeleteTableUseCase,
    ):
        self.floor_repo = floor_repo
        self.zone_repo = zone_repo
        self.table_repo = table_repo
        self.force_delete_table_use_case = force_delete_table_use_case

    def execute(self, floor_id: int) -> None:
        floor = self.floor_repo.get_by_id(floor_id)
        if floor is None:
            raise ValidationError("Floor not found")

        tables_on_floor = self.table_repo.search(TableFilters(floor=floor.number))
        for table in tables_on_floor:
            self.force_delete_table_use_case.execute(table.id)

        zones_on_floor = self.zone_repo.list(floor=floor.number)
        for zone in zones_on_floor:
            self.zone_repo.delete(zone.id)

        self.floor_repo.delete(floor_id)