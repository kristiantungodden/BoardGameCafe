from features.games.application.interfaces.game_copy_repository_interface import GameCopyRepository
from features.games.application.interfaces.incident_repository_interface import IncidentRepositoryInterface
from features.games.application.use_cases.game_copy_use_cases import (
    ListGameCopiesUseCase,
    UpdateGameCopyStatusUseCase,
)
from features.games.application.use_cases.incident_use_cases import (
    ListIncidentsForGameCopyUseCase,
    ListIncidentsUseCase,
    ReportIncidentUseCase,
    DeleteIncidentUseCase,
)
from features.games.infrastructure.repositories.game_copy_repository import GameCopyRepositoryImpl
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
from features.bookings.application.use_cases.booking_lifecycle_use_cases import (
    CompleteBookingUseCase,
    MarkBookingNoShowUseCase,
    SeatBookingUseCase,
)
from features.reservations.infrastructure.repositories.game_reservation_repository import (
    SqlAlchemyGameReservationRepository,
)
from features.reservations.infrastructure.repositories.waitlist_repository import (
    SqlAlchemyWaitlistRepository,
)
from features.reservations.application.use_cases.waitlist_use_cases import (
    ListWaitlistUseCase,
    AddToWaitlistUseCase,
    RemoveFromWaitlistUseCase,
)
from features.reservations.infrastructure.repositories.reservation_repository import (
    SqlAlchemyReservationRepository,
)
from features.bookings.infrastructure.repositories.booking_status_history_repository import (
    SqlAlchemyBookingStatusHistoryRepository,
)


# --- Repository factories ---

def get_reservation_repo() -> ReservationRepositoryInterface:
    return SqlAlchemyReservationRepository()


def get_game_copy_repo() -> GameCopyRepository:
    return GameCopyRepositoryImpl()


def get_game_reservation_repo() -> GameReservationRepositoryInterface:
    return SqlAlchemyGameReservationRepository()


def get_incident_repo() -> IncidentRepositoryInterface:
    return SqlAlchemyIncidentRepository()


def get_waitlist_repo():
    return SqlAlchemyWaitlistRepository()


def get_status_history_repo():
    return SqlAlchemyBookingStatusHistoryRepository()


# --- Workflow 2: View reservations ---

def get_list_confirmed_reservations_use_case() -> ListConfirmedReservationsUseCase:
    return ListConfirmedReservationsUseCase(get_reservation_repo())


def get_list_seated_reservations_use_case() -> ListSeatedReservationsUseCase:
    return ListSeatedReservationsUseCase(get_reservation_repo())


def get_list_active_reservations_use_case() -> ListActiveReservationsUseCase:
    return ListActiveReservationsUseCase(get_reservation_repo())


# --- Workflow 3: Seat parties / update status ---

def get_seat_reservation_use_case() -> SeatBookingUseCase:
    return SeatBookingUseCase(get_reservation_repo(), get_status_history_repo())


def get_complete_reservation_use_case() -> CompleteBookingUseCase:
    return CompleteBookingUseCase(get_reservation_repo(), get_status_history_repo())


def get_no_show_reservation_use_case() -> MarkBookingNoShowUseCase:
    return MarkBookingNoShowUseCase(get_reservation_repo(), get_status_history_repo())


# --- Workflow 4: Assign / swap games ---

def get_swap_game_copy_use_case() -> SwapGameCopyUseCase:
    return SwapGameCopyUseCase(
        game_copy_repo=get_game_copy_repo(),
        game_reservation_repo=get_game_reservation_repo(),
    )


def get_update_reservation_use_case() -> UpdateReservationUseCase:
    return UpdateReservationUseCase(get_reservation_repo())


# --- Workflow 5: Check out / check in game copies ---

def get_update_game_copy_status_use_case() -> UpdateGameCopyStatusUseCase:
    return UpdateGameCopyStatusUseCase(get_game_copy_repo())


def get_list_game_copies_use_case() -> ListGameCopiesUseCase:
    return ListGameCopiesUseCase(get_game_copy_repo())


# --- Workflow 6: Incidents ---

def get_report_incident_use_case() -> ReportIncidentUseCase:
    return ReportIncidentUseCase(
        incident_repo=get_incident_repo(),
        game_copy_repo=get_game_copy_repo(),
    )


def get_list_incidents_use_case() -> ListIncidentsUseCase:
    return ListIncidentsUseCase(get_incident_repo())


def get_list_incidents_for_game_copy_use_case() -> ListIncidentsForGameCopyUseCase:
    return ListIncidentsForGameCopyUseCase(get_incident_repo())


def get_delete_incident_use_case() -> DeleteIncidentUseCase:
    return DeleteIncidentUseCase(get_incident_repo())


def get_list_waitlist_use_case() -> ListWaitlistUseCase:
    return ListWaitlistUseCase(get_waitlist_repo())


def get_add_waitlist_use_case() -> AddToWaitlistUseCase:
    return AddToWaitlistUseCase(get_waitlist_repo())


def get_remove_waitlist_use_case() -> RemoveFromWaitlistUseCase:
    return RemoveFromWaitlistUseCase(get_waitlist_repo())