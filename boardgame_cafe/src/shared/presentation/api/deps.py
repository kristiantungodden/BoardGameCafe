from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationCommand,
    AddGameToReservationUseCase,
    ListReservationGamesUseCase,
    RemoveGameFromReservationUseCase,
)
from features.reservations.application.use_cases.reservation_lookup_use_cases import (
    GetReservationLookupUseCase,
)
from features.reservations.application.use_cases.booking_use_cases import (
    CreateBookingUseCase,
    BookingGameRequest,
)
from features.reservations.application.use_cases.booking_availability_use_cases import (
    GetBookingAvailabilityUseCase,
)
from features.tables.application.use_cases.table_availability_use_case import (
    GetTableAvailabilityUseCase,
)
from features.payments.application.use_cases.payment_use_cases import create_and_save_payment
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.reservations.application.use_cases.reservation_use_cases import (
    CancelReservationUseCase,
    CompleteReservationUseCase,
    CreateReservationUseCase,
    GetReservationByIdUseCase,
    ListReservationsUseCase,
    MarkReservationNoShowUseCase,
    SeatReservationUseCase,
    CreateReservationCommand,
)
from features.reservations.infrastructure.repositories.game_reservation_repository import (
    SqlAlchemyGameReservationRepository,
)
from features.reservations.infrastructure.repositories.reservation_lookup_repository import (
    SqlAlchemyReservationLookupRepository,
)
from features.reservations.infrastructure.repositories.reservation_repository import SqlAlchemyReservationRepository
from features.reservations.infrastructure.repositories.available_table_repository import (
    SqlAlchemyAvailableTableRepository,
)
from features.reservations.infrastructure.repositories.available_game_copy_repository import (
    SqlAlchemyAvailableGameCopyRepository,
)
from features.tables.infrastructure.repositories.table_repository import TableRepository
from shared.domain.exceptions import ValidationError
from shared.infrastructure import db

_repo = SqlAlchemyReservationRepository()
_game_repo = SqlAlchemyGameReservationRepository()
_lookup_repo = SqlAlchemyReservationLookupRepository()
_payment_repo = PaymentRepository()
_available_table_repo = SqlAlchemyAvailableTableRepository()
_available_copy_repo = SqlAlchemyAvailableGameCopyRepository()
_table_repo = TableRepository()



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


def get_list_reservation_games_use_case() -> ListReservationGamesUseCase:
    return ListReservationGamesUseCase(_repo, _game_repo)


def get_reservation_lookup_use_case() -> GetReservationLookupUseCase:
    return GetReservationLookupUseCase(_lookup_repo)


def get_create_reservation_payment_handler():
    def _create_payment_for_reservation(reservation):
        return create_and_save_payment(reservation, _payment_repo)

    return _create_payment_for_reservation


def get_create_reservation_with_payment_handler():
    def _create_reservation_with_payment(cmd: CreateReservationCommand):
        session = db.session()
        tx_ctx = session.begin_nested() if session.in_transaction() else session.begin()

        with tx_ctx:
            reservation_repo = SqlAlchemyReservationRepository(
                session=session,
                auto_commit=False,
            )
            payment_repo = PaymentRepository(session=session, auto_commit=False)

            reservation_use_case = CreateReservationUseCase(reservation_repo)
            reservation = reservation_use_case.execute(cmd)
            payment = create_and_save_payment(reservation, payment_repo)

        return reservation, payment

    return _create_reservation_with_payment


def get_create_booking_handler():
    def _create_booking(cmd: CreateReservationCommand, games: list[dict] | None = None):
        booking_use_case = CreateBookingUseCase(
            reservation_repo=_repo,
            game_repo=_game_repo,
            available_table_repo=_available_table_repo,
            available_copy_repo=_available_copy_repo,
            payment_repo=_payment_repo,
        )

        game_requests = [
            BookingGameRequest(
                requested_game_id=game["requested_game_id"],
                game_copy_id=game.get("game_copy_id"),
            )
            for game in (games or [])
        ]

        return booking_use_case.execute(
            customer_id=cmd.customer_id,
            table_id=cmd.table_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            party_size=cmd.party_size,
            games=game_requests,
            notes=cmd.notes,
        )

    return _create_booking


def get_booking_availability_handler():
    def _get_availability(start_ts, end_ts, party_size):
        availability_use_case = GetBookingAvailabilityUseCase(
            available_table_repo=_available_table_repo,
            available_copy_repo=_available_copy_repo,
        )
        return availability_use_case.execute(start_ts, end_ts, party_size)

    return _get_availability


def get_table_availability_use_case() -> GetTableAvailabilityUseCase:
    return GetTableAvailabilityUseCase(_table_repo, _repo)