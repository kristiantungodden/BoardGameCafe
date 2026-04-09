from features.reservations.infrastructure.repositories.reservation_repository import (
    SqlAlchemyReservationRepository,
)
from features.tables.application.use_cases.table_availability_use_case import (
    GetTableAvailabilityUseCase,
)
from features.tables.infrastructure.repositories.table_repository import TableRepository

_table_repo = TableRepository()
_reservation_repo = SqlAlchemyReservationRepository()


def get_table_availability_use_case() -> GetTableAvailabilityUseCase:
    return GetTableAvailabilityUseCase(_table_repo, _reservation_repo)


__all__ = ["get_table_availability_use_case"]
