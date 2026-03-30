from features.reservations.application.use_cases.reservation_use_cases import (
    CancelReservationUseCase,
    CompleteReservationUseCase,
    CreateReservationUseCase,
    GetReservationByIdUseCase,
    ListReservationsUseCase,
    MarkReservationNoShowUseCase,
    SeatReservationUseCase,
)
from features.reservations.infrastructure.repositories.reservation_repository import SqlAlchemyReservationRepository

_repo = SqlAlchemyReservationRepository()


def get_create_reservation_use_case() -> CreateReservationUseCase:
    return CreateReservationUseCase(_repo)


def get_list_reservations_use_case() -> ListReservationsUseCase:
    return ListReservationsUseCase(_repo)


def get_reservation_by_id_use_case() -> GetReservationByIdUseCase:
    return GetReservationByIdUseCase(_repo)


def get_cancel_reservation_use_case() -> CancelReservationUseCase:
    return CancelReservationUseCase(_repo)


def get_seat_reservation_use_case() -> SeatReservationUseCase:
    return SeatReservationUseCase(_repo)


def get_complete_reservation_use_case() -> CompleteReservationUseCase:
    return CompleteReservationUseCase(_repo)


def get_no_show_reservation_use_case() -> MarkReservationNoShowUseCase:
    return MarkReservationNoShowUseCase(_repo)