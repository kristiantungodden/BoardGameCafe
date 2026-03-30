from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationUseCase,
    RemoveGameFromReservationUseCase,
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
from features.reservations.infrastructure.repositories.reservation_repository import SqlAlchemyReservationRepository
from shared.infrastructure import db

_repo = SqlAlchemyReservationRepository()
_game_repo = SqlAlchemyGameReservationRepository()
_payment_repo = PaymentRepository()


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


def get_create_reservation_payment_handler():
    def _create_payment_for_reservation(reservation):
        return create_and_save_payment(reservation, _payment_repo)

    return _create_payment_for_reservation


def get_create_reservation_with_payment_handler():
    def _create_reservation_with_payment(cmd: CreateReservationCommand):
        with db.session.begin():
            reservation_repo = SqlAlchemyReservationRepository(
                session=db.session,
                auto_commit=False,
            )
            payment_repo = PaymentRepository(session=db.session, auto_commit=False)

            reservation_use_case = CreateReservationUseCase(reservation_repo)
            reservation = reservation_use_case.execute(cmd)
            payment = create_and_save_payment(reservation, payment_repo)

        return reservation, payment

    return _create_reservation_with_payment