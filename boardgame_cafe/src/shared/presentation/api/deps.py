from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationUseCase,
    RemoveGameFromReservationUseCase,
)
from features.reservations.application.use_cases.reservation_use_cases import (
    CancelReservationUseCase,
    CompleteReservationUseCase,
    CreateReservationUseCase,
    GetReservationByIdUseCase,
    ListReservationsUseCase,
    MarkReservationNoShowUseCase,
    SeatReservationUseCase,
)
from features.reservations.infrastructure.repositories.game_reservation_repository import (
    SqlAlchemyGameReservationRepository,
)
from features.reservations.infrastructure.repositories.reservation_repository import SqlAlchemyReservationRepository

_repo = SqlAlchemyReservationRepository()
_game_repo = SqlAlchemyGameReservationRepository()


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


def get_add_game_to_reservation_use_case() -> AddGameToReservationUseCase:
    return AddGameToReservationUseCase(_repo, _game_repo)


def get_remove_game_from_reservation_use_case() -> RemoveGameFromReservationUseCase:
    return RemoveGameFromReservationUseCase(_repo, _game_repo)