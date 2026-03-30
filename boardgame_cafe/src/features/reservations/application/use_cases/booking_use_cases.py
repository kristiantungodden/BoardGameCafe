from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from features.reservations.application.interfaces.available_game_copy_repository_interface import (
    AvailableGameCopyRepositoryInterface,
)
from features.reservations.application.interfaces.available_table_repository_interface import (
    AvailableTableRepositoryInterface,
)
from features.reservations.application.interfaces.reservation_repository_interface import (
    ReservationRepositoryInterface,
)
from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationCommand,
    AddGameToReservationUseCase,
)
from features.reservations.application.use_cases.reservation_use_cases import (
    CreateReservationCommand,
    CreateReservationUseCase,
)
from features.payments.application.use_cases.payment_use_cases import create_and_save_payment
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.reservations.infrastructure.repositories.game_reservation_repository import (
    SqlAlchemyGameReservationRepository,
)
from shared.domain.exceptions import ValidationError
from shared.infrastructure import db


@dataclass
class BookingGameRequest:
    requested_game_id: int
    game_copy_id: Optional[int] = None


class CreateBookingUseCase:
    """Use case for creating a complete booking with auto-table and auto-game-copy selection."""

    def __init__(
        self,
        reservation_repo: ReservationRepositoryInterface,
        game_repo,
        available_table_repo: AvailableTableRepositoryInterface,
        available_copy_repo: AvailableGameCopyRepositoryInterface,
        payment_repo: PaymentRepository,
    ):
        self.reservation_repo = reservation_repo
        self.game_repo = game_repo
        self.available_table_repo = available_table_repo
        self.available_copy_repo = available_copy_repo
        self.payment_repo = payment_repo

    def execute(
        self,
        customer_id: int,
        table_id: Optional[int],
        start_ts: datetime,
        end_ts: datetime,
        party_size: int,
        games: list[BookingGameRequest],
        notes: Optional[str] = None,
    ):
        """Execute the booking with auto-selection and atomic transaction."""
        session = db.session()
        tx_ctx = session.begin_nested() if session.in_transaction() else session.begin()

        with tx_ctx:
            reservation_repo = self.reservation_repo.__class__(
                session=session,
                auto_commit=False,
            )
            game_repo = self.game_repo.__class__(
                session=session,
                auto_commit=False,
            )
            payment_repo = PaymentRepository(session=session, auto_commit=False)

            # Auto-select table if not provided
            selected_table_id = table_id
            if selected_table_id is None:
                selected_table_id = self.available_table_repo.find_best_available_table(
                    party_size, start_ts, end_ts
                )
                if selected_table_id is None:
                    raise ValidationError("No suitable table is available for the selected timeslot")

            # Create reservation
            reservation_cmd = CreateReservationCommand(
                customer_id=customer_id,
                table_id=selected_table_id,
                start_ts=start_ts,
                end_ts=end_ts,
                party_size=party_size,
                notes=notes,
            )
            reservation_use_case = CreateReservationUseCase(reservation_repo)
            reservation = reservation_use_case.execute(reservation_cmd)

            # Add games with auto-copy selection
            created_games = []
            add_game_use_case = AddGameToReservationUseCase(reservation_repo, game_repo)

            for game_request in games:
                requested_game_id = game_request.requested_game_id
                requested_copy_id = game_request.game_copy_id

                # Auto-select copy if not provided
                if requested_copy_id is None:
                    requested_copy_id = self.available_copy_repo.find_available_copy_id(
                        requested_game_id, start_ts, end_ts
                    )
                    if requested_copy_id is None:
                        raise ValidationError(
                            f"No available copy for game {requested_game_id} in selected timeslot"
                        )
                else:
                    # Validate the requested copy
                    if not self.available_copy_repo.validate_copy_available(
                        requested_copy_id, requested_game_id, start_ts, end_ts
                    ):
                        raise ValidationError(
                            "Selected game copy is unavailable for the selected timeslot"
                        )

                created_games.append(
                    add_game_use_case.execute(
                        AddGameToReservationCommand(
                            reservation_id=reservation.id,
                            requested_game_id=requested_game_id,
                            game_copy_id=requested_copy_id,
                        )
                    )
                )

            # Create payment atomically
            payment = create_and_save_payment(reservation, payment_repo)

        return reservation, created_games, payment
