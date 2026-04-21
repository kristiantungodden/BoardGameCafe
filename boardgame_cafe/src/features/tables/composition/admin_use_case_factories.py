from features.reservations.infrastructure.repositories.reservation_repository import SqlAlchemyReservationRepository
from features.tables.infrastructure.repositories.floor_repository import FloorRepository
from features.tables.infrastructure.repositories.table_repository import TableRepository
from features.tables.infrastructure.repositories.zone_repository import ZoneRepository
from features.tables.application.use_cases.admin_table_use_cases import (
    CreateZoneUseCase,
    CreateFloorUseCase,
    CreateTableUseCase,
    DeleteFloorUseCase,
    DeleteTableUseCase,
    DeleteZoneUseCase,
    ListFloorsUseCase,
    ListTablesUseCase,
    ListZonesUseCase,
    UpdateFloorUseCase,
    UpdateTableUseCase,
    UpdateZoneUseCase,
)

_floor_repo = FloorRepository()
_table_repo = TableRepository()
_zone_repo = ZoneRepository()
_reservation_repo = SqlAlchemyReservationRepository()


def get_list_floors_use_case() -> ListFloorsUseCase:
    return ListFloorsUseCase(_floor_repo)


def get_create_floor_use_case() -> CreateFloorUseCase:
    return CreateFloorUseCase(_floor_repo)


def get_update_floor_use_case() -> UpdateFloorUseCase:
    return UpdateFloorUseCase(_floor_repo)


def get_delete_floor_use_case() -> DeleteFloorUseCase:
    return DeleteFloorUseCase(_floor_repo, _table_repo)


def get_list_tables_use_case() -> ListTablesUseCase:
    return ListTablesUseCase(_table_repo)


def get_create_table_use_case() -> CreateTableUseCase:
    return CreateTableUseCase(_table_repo, _floor_repo, _zone_repo)


def get_update_table_use_case() -> UpdateTableUseCase:
    return UpdateTableUseCase(_table_repo, _floor_repo, _zone_repo, _reservation_repo)


def get_delete_table_use_case() -> DeleteTableUseCase:
    return DeleteTableUseCase(_table_repo, _reservation_repo)


def get_list_zones_use_case() -> ListZonesUseCase:
    return ListZonesUseCase(_zone_repo)


def get_create_zone_use_case() -> CreateZoneUseCase:
    return CreateZoneUseCase(_floor_repo, _zone_repo)


def get_update_zone_use_case() -> UpdateZoneUseCase:
    return UpdateZoneUseCase(_floor_repo, _zone_repo, _table_repo)


def get_delete_zone_use_case() -> DeleteZoneUseCase:
    return DeleteZoneUseCase(_zone_repo, _table_repo)