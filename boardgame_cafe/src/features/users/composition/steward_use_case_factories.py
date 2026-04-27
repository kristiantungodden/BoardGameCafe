from features.games.application.interfaces.game_copy_repository_interface import GameCopyRepository
from features.games.application.interfaces.incident_repository_interface import IncidentRepositoryInterface
from features.games.application.use_cases.game_copy_use_cases import (
    ListGameCopiesUseCase,
    UpdateGameCopyStatusUseCase,
)
from features.games.application.use_cases.game_copy_browse_use_cases import (
    BrowseGameCopiesUseCase,
)
from features.games.application.use_cases.incident_use_cases import (
    ListIncidentsForGameCopyUseCase,
    ListIncidentsUseCase,
    ReportIncidentUseCase,
    DeleteIncidentUseCase,
)
from features.games.infrastructure.repositories.game_copy_repository import GameCopyRepositoryImpl
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.infrastructure.repositories.incident_repository import SqlAlchemyIncidentRepository
from features.reservations.application.interfaces.game_reservation_repository_interface import (
    GameReservationRepositoryInterface,
)
from features.reservations.application.interfaces.reservation_repository_interface import (
    ReservationRepositoryInterface,
)
from features.reservations.application.use_cases.reservation_game_use_cases import (
    SwapGameCopyUseCase,
)
from features.reservations.application.use_cases.reservation_use_cases import (
    ListActiveReservationsUseCase,
    ListConfirmedReservationsUseCase,
    ListSeatedReservationsUseCase,
    UpdateReservationUseCase,
)
from features.reservations.application.use_cases.steward_reservation_browse_use_cases import (
    BrowseStewardReservationsUseCase,
)
from features.bookings.application.use_cases.booking_lifecycle_use_cases import (
    CompleteBookingUseCase,
    MarkBookingNoShowUseCase,
    SeatBookingUseCase,
)
from features.reservations.infrastructure.repositories.table_reservation_repository import (
    SqlAlchemyTableReservationRepository,
)
from features.tables.infrastructure.repositories.table_repository import (
    TableRepository as SqlAlchemyTableRepository,
)
from features.reservations.infrastructure.repositories.game_reservation_repository import (
    SqlAlchemyGameReservationRepository,
)
from features.reservations.infrastructure.repositories.reservation_repository import (
    SqlAlchemyReservationRepository,
)
from features.bookings.infrastructure.repositories.booking_status_history_repository import (
    SqlAlchemyBookingStatusHistoryRepository,
)
from features.users.infrastructure.repositories.user_repository import SqlAlchemyUserRepository


def get_reservation_repo() -> ReservationRepositoryInterface:
    return SqlAlchemyReservationRepository()


def get_game_copy_repo() -> GameCopyRepository:
    return GameCopyRepositoryImpl()


def get_game_reservation_repo() -> GameReservationRepositoryInterface:
    return SqlAlchemyGameReservationRepository()


def get_incident_repo() -> IncidentRepositoryInterface:
    return SqlAlchemyIncidentRepository()


def get_status_history_repo():
    return SqlAlchemyBookingStatusHistoryRepository()


def get_list_confirmed_reservations_use_case() -> ListConfirmedReservationsUseCase:
    return ListConfirmedReservationsUseCase(get_reservation_repo())


def get_list_seated_reservations_use_case() -> ListSeatedReservationsUseCase:
    return ListSeatedReservationsUseCase(get_reservation_repo())


def get_list_active_reservations_use_case() -> ListActiveReservationsUseCase:
    return ListActiveReservationsUseCase(get_reservation_repo())


def get_browse_steward_reservations_use_case() -> BrowseStewardReservationsUseCase:
    return BrowseStewardReservationsUseCase(
        reservation_repo=get_reservation_repo(),
        user_repo=SqlAlchemyUserRepository(),
    )


def get_seat_reservation_use_case() -> SeatBookingUseCase:
    return SeatBookingUseCase(
        get_reservation_repo(),
        get_status_history_repo(),
        SqlAlchemyTableReservationRepository(),
        SqlAlchemyTableRepository(),
    )


def get_complete_reservation_use_case() -> CompleteBookingUseCase:
    return CompleteBookingUseCase(
        get_reservation_repo(),
        get_status_history_repo(),
        SqlAlchemyTableReservationRepository(),
        SqlAlchemyTableRepository(),
    )


def get_no_show_reservation_use_case() -> MarkBookingNoShowUseCase:
    return MarkBookingNoShowUseCase(get_reservation_repo(), get_status_history_repo())


def get_swap_game_copy_use_case() -> SwapGameCopyUseCase:
    return SwapGameCopyUseCase(
        game_copy_repo=get_game_copy_repo(),
        game_reservation_repo=get_game_reservation_repo(),
    )


def get_update_reservation_use_case() -> UpdateReservationUseCase:
    return UpdateReservationUseCase(get_reservation_repo())


def get_update_game_copy_status_use_case() -> UpdateGameCopyStatusUseCase:
    return UpdateGameCopyStatusUseCase(get_game_copy_repo())


def get_list_game_copies_use_case() -> ListGameCopiesUseCase:
    return ListGameCopiesUseCase(get_game_copy_repo())


def get_browse_game_copies_use_case() -> BrowseGameCopiesUseCase:
    return BrowseGameCopiesUseCase(
        game_copy_repo=get_game_copy_repo(),
        game_repo=GameRepository(),
    )


def get_report_incident_use_case(event_bus=None) -> ReportIncidentUseCase:
    return ReportIncidentUseCase(
        incident_repo=get_incident_repo(),
        game_copy_repo=get_game_copy_repo(),
        event_bus=event_bus,
    )


def get_list_incidents_use_case() -> ListIncidentsUseCase:
    return ListIncidentsUseCase(get_incident_repo())


def get_list_incidents_for_game_copy_use_case() -> ListIncidentsForGameCopyUseCase:
    return ListIncidentsForGameCopyUseCase(get_incident_repo())


def get_delete_incident_use_case(event_bus=None) -> DeleteIncidentUseCase:
    return DeleteIncidentUseCase(get_incident_repo(), event_bus=event_bus)
