from features.reservations.application.use_cases.reservation_use_cases import (
    CreateReservationUseCase,
    GetReservationByIdUseCase,
    ListReservationsUseCase,
)
from features.reservations.infrastructure.repositories.reservation_repository import InMemoryReservationRepository

_repo = InMemoryReservationRepository()


def get_create_reservation_use_case() -> CreateReservationUseCase:
    return CreateReservationUseCase(_repo)


def get_list_reservations_use_case() -> ListReservationsUseCase:
    return ListReservationsUseCase(_repo)


def get_reservation_by_id_use_case() -> GetReservationByIdUseCase:
    return GetReservationByIdUseCase(_repo)