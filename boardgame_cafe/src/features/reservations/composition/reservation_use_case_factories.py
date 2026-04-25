import os

from features.bookings.application.use_cases.booking_lifecycle_use_cases import (
    BookingCommand,
    CancelBookingUseCase,
    CompleteBookingUseCase,
    CreateBookingRecordUseCase,
    GetBookingByIdUseCase,
    ListBookingStatusHistoryUseCase,
    ListBookingsUseCase,
    MarkBookingNoShowUseCase,
    SeatBookingUseCase,
)
from features.bookings.application.use_cases.booking_use_cases import (
    BookingGameRequest,
    CreateBookingUseCase,
)
from features.bookings.infrastructure.repositories.booking_repository import (
    SqlAlchemyBookingRepository,
)
from features.bookings.infrastructure.repositories.booking_status_history_repository import (
    SqlAlchemyBookingStatusHistoryRepository,
)
from features.payments.application.use_cases.payment_use_cases import create_and_save_payment
from features.payments.infrastructure.stripe.stripe_adapter import StripeAdapter
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.reservations.application.use_cases.booking_availability_use_cases import (
    GetBookingAvailabilityUseCase,
)
from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationUseCase,
    ListReservationGamesUseCase,
    RemoveGameFromReservationUseCase,
)
from features.reservations.application.use_cases.reservation_lookup_use_cases import (
    GetReservationLookupUseCase,
)
from features.reservations.infrastructure.repositories.available_game_copy_repository import (
    SqlAlchemyAvailableGameCopyRepository,
)
from features.reservations.infrastructure.repositories.available_table_repository import (
    SqlAlchemyAvailableTableRepository,
)
from features.reservations.infrastructure.repositories.game_reservation_repository import (
    SqlAlchemyGameReservationRepository,
)
from features.reservations.infrastructure.repositories.reservation_lookup_repository import (
    SqlAlchemyReservationLookupRepository,
)
from features.reservations.infrastructure.repositories.reservation_repository import (
    SqlAlchemyReservationRepository,
)
from features.reservations.infrastructure.repositories.table_reservation_repository import (
    SqlAlchemyTableReservationRepository,
)
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.infrastructure.repositories.game_copy_repository import GameCopyRepositoryImpl
from features.tables.infrastructure.repositories.table_repository import (
    TableRepository as SqlAlchemyTableRepository,
)
from features.users.infrastructure.pricing_settings import resolve_base_fee
from shared.infrastructure import db

_repo = SqlAlchemyReservationRepository()
_booking_repo = SqlAlchemyBookingRepository()
_table_reservation_repo = SqlAlchemyTableReservationRepository()
_table_repo = SqlAlchemyTableRepository()
_game_repo = SqlAlchemyGameReservationRepository()
_lookup_repo = SqlAlchemyReservationLookupRepository()
_payment_repo = PaymentRepository()
_stripe_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
_stripe_provider = (
    StripeAdapter(_stripe_key, os.getenv("APP_BASE_URL") or "http://127.0.0.1:5000")
    if _stripe_key
    else None
)
_status_history_repo = SqlAlchemyBookingStatusHistoryRepository()
_available_table_repo = SqlAlchemyAvailableTableRepository()
_available_copy_repo = SqlAlchemyAvailableGameCopyRepository()
_game_lookup_repo = GameRepository()
_game_copy_repo = GameCopyRepositoryImpl()


def get_create_reservation_use_case() -> CreateBookingRecordUseCase:
    return CreateBookingRecordUseCase(
        _booking_repo,
        _table_reservation_repo,
        _status_history_repo,
    )


def get_list_reservations_use_case() -> ListBookingsUseCase:
    return ListBookingsUseCase(_repo)


def get_reservation_by_id_use_case() -> GetBookingByIdUseCase:
    return GetBookingByIdUseCase(_repo)


def get_cancel_reservation_use_case() -> CancelBookingUseCase:
    return CancelBookingUseCase(
        _repo,
        _status_history_repo,
        payment_repo=_payment_repo,
        payment_provider=_stripe_provider,
    )


def get_seat_reservation_use_case() -> SeatBookingUseCase:
    return SeatBookingUseCase(_repo, _status_history_repo, _table_reservation_repo, _table_repo)


def get_complete_reservation_use_case() -> CompleteBookingUseCase:
    return CompleteBookingUseCase(_repo, _status_history_repo, _table_reservation_repo, _table_repo)


def get_no_show_reservation_use_case() -> MarkBookingNoShowUseCase:
    return MarkBookingNoShowUseCase(_repo, _status_history_repo)


def get_reservation_status_history_use_case() -> ListBookingStatusHistoryUseCase:
    return ListBookingStatusHistoryUseCase(_status_history_repo)


def get_add_game_to_reservation_use_case() -> AddGameToReservationUseCase:
    return AddGameToReservationUseCase(_booking_repo, _game_repo)


def get_remove_game_from_reservation_use_case() -> RemoveGameFromReservationUseCase:
    return RemoveGameFromReservationUseCase(_booking_repo, _game_repo)


def get_list_reservation_games_use_case() -> ListReservationGamesUseCase:
    return ListReservationGamesUseCase(_booking_repo, _game_repo)


def get_reservation_lookup_use_case() -> GetReservationLookupUseCase:
    return GetReservationLookupUseCase(_lookup_repo)


def get_create_reservation_payment_handler():
    def _create_payment_for_reservation(reservation):
        return create_and_save_payment(reservation, _payment_repo)

    return _create_payment_for_reservation


def get_create_reservation_with_payment_handler():
    def _create_reservation_with_payment(cmd: BookingCommand):
        session = db.session()
        tx_ctx = session.begin_nested() if session.in_transaction() else session.begin()

        with tx_ctx:
            booking_repo = SqlAlchemyBookingRepository(
                session=session,
                auto_commit=False,
            )
            table_reservation_repo = SqlAlchemyTableReservationRepository(
                session=session,
                auto_commit=False,
            )
            payment_repo = PaymentRepository(session=session, auto_commit=False)

            booking = CreateBookingRecordUseCase(
                booking_repo=booking_repo,
                table_reservation_repo=table_reservation_repo,
                status_history_repo=SqlAlchemyBookingStatusHistoryRepository(
                    session=session,
                    auto_commit=False,
                ),
            ).execute(cmd)
            payment = create_and_save_payment(booking, payment_repo)

        return booking, payment

    return _create_reservation_with_payment


def get_create_booking_handler():
    def _create_booking(cmd: BookingCommand, games: list[dict] | None = None):
        session = db.session()
        tx_ctx = session.begin_nested() if session.in_transaction() else session.begin()

        with tx_ctx:
            booking_repo = SqlAlchemyBookingRepository(session=session, auto_commit=False)
            table_reservation_repo = SqlAlchemyTableReservationRepository(
                session=session,
                auto_commit=False,
            )
            game_reservation_repo = SqlAlchemyGameReservationRepository(
                session=session,
                auto_commit=False,
            )
            table_repo = SqlAlchemyTableRepository(session=session, auto_commit=False)
            game_lookup_repo = GameRepository(session=session)
            available_table_repo = SqlAlchemyAvailableTableRepository(session=session)
            available_copy_repo = SqlAlchemyAvailableGameCopyRepository(session=session)
            payment_repo = PaymentRepository(session=session, auto_commit=False)
            status_history_repo = SqlAlchemyBookingStatusHistoryRepository(
                session=session,
                auto_commit=False,
            )
            base_fee_cents = resolve_base_fee(session)["effective_fee_cents"]

            booking_use_case = CreateBookingUseCase(
                booking_repo=booking_repo,
                table_reservation_repo=table_reservation_repo,
                game_repo=game_reservation_repo,
                table_repo=table_repo,
                game_lookup_repo=game_lookup_repo,
                available_table_repo=available_table_repo,
                available_copy_repo=available_copy_repo,
                payment_repo=payment_repo,
                status_history_repo=status_history_repo,
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
                table_ids=getattr(cmd, "table_ids", None),
                start_ts=cmd.start_ts,
                end_ts=cmd.end_ts,
                party_size=cmd.party_size,
                games=game_requests,
                notes=cmd.notes,
                base_fee_cents=base_fee_cents,
            )

    return _create_booking


def get_booking_availability_handler():
    def _get_availability(start_ts, end_ts, party_size):
        availability_use_case = GetBookingAvailabilityUseCase(
            available_table_repo=_available_table_repo,
            available_copy_repo=_available_copy_repo,
            table_repo=_table_repo,
            game_copy_repo=_game_copy_repo,
        )
        return availability_use_case.execute(start_ts, end_ts, party_size)

    return _get_availability


__all__ = [
    "get_add_game_to_reservation_use_case",
    "get_booking_availability_handler",
    "get_cancel_reservation_use_case",
    "get_complete_reservation_use_case",
    "get_create_booking_handler",
    "get_create_reservation_payment_handler",
    "get_create_reservation_use_case",
    "get_create_reservation_with_payment_handler",
    "get_list_reservation_games_use_case",
    "get_list_reservations_use_case",
    "get_no_show_reservation_use_case",
    "get_remove_game_from_reservation_use_case",
    "get_reservation_by_id_use_case",
    "get_reservation_lookup_use_case",
    "get_reservation_status_history_use_case",
    "get_seat_reservation_use_case",
]