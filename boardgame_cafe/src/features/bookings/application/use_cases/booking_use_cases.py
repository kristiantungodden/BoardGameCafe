from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from features.bookings.application.use_cases.booking_lifecycle_use_cases import (
    BookingCommand,
    CreateBookingRecordUseCase,
)
from features.bookings.application.interfaces.booking_status_history_repository_interface import (
    BookingStatusHistoryRepositoryInterface,
)
from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.application.use_cases.payment_use_cases import create_and_save_payment
from features.reservations.application.interfaces.available_game_copy_repository_interface import (
    AvailableGameCopyRepositoryInterface,
)
from features.reservations.application.interfaces.available_table_repository_interface import (
    AvailableTableRepositoryInterface,
)
from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationCommand,
    AddGameToReservationUseCase,
)
from features.reservations.domain.models.table_reservation import TableReservation
from shared.domain.exceptions import ValidationError
from shared.infrastructure import db


@dataclass
class BookingGameRequest:
    requested_game_id: int
    game_copy_id: Optional[int] = None


class CreateBookingUseCase:
    def __init__(
        self,
        booking_repo,
        table_reservation_repo,
        game_repo,
        available_table_repo: AvailableTableRepositoryInterface,
        available_copy_repo: AvailableGameCopyRepositoryInterface,
        payment_repo: PaymentRepositoryInterface,
        status_history_repo: BookingStatusHistoryRepositoryInterface | None = None,
    ):
        self.booking_repo = booking_repo
        self.table_reservation_repo = table_reservation_repo
        self.game_repo = game_repo
        self.available_table_repo = available_table_repo
        self.available_copy_repo = available_copy_repo
        self.payment_repo = payment_repo
        self.status_history_repo = status_history_repo

    def execute(
        self,
        customer_id: int,
        table_id: Optional[int],
        start_ts: datetime,
        end_ts: datetime,
        party_size: int,
        games: list[BookingGameRequest],
        notes: Optional[str] = None,
        table_ids: Optional[list[int]] = None,
    ):
        session = db.session()
        tx_ctx = session.begin_nested() if session.in_transaction() else session.begin()

        with tx_ctx:
            booking_repo = self.booking_repo.__class__(session=session, auto_commit=False)
            table_reservation_repo = self.table_reservation_repo.__class__(
                session=session, auto_commit=False
            )
            game_repo = self.game_repo.__class__(session=session, auto_commit=False)
            available_table_repo = self.available_table_repo.__class__(session=session)
            available_copy_repo = self.available_copy_repo.__class__(session=session)
            payment_repo = (
                None
                if self.payment_repo is None
                else self.payment_repo.__class__(session=session, auto_commit=False)
            )
            status_history_repo = (
                None
                if self.status_history_repo is None
                else self.status_history_repo.__class__(session=session, auto_commit=False)
            )

            selected_table_ids = list(dict.fromkeys(table_ids or []))

            selected_table_id = table_id
            if selected_table_ids:
                if selected_table_id is not None and selected_table_id not in selected_table_ids:
                    selected_table_ids.insert(0, selected_table_id)

                minimum_party = party_size if len(selected_table_ids) == 1 else 1
                for selected_id in selected_table_ids:
                    if not available_table_repo.validate_table_selection(
                        selected_id, minimum_party, start_ts, end_ts
                    ):
                        raise ValidationError(
                            "One or more selected tables are unavailable for the selected timeslot"
                        )
                selected_table_id = selected_table_ids[0]
            elif selected_table_id is None:
                selected_table_id = available_table_repo.find_best_available_table(
                    party_size, start_ts, end_ts
                )
                if selected_table_id is None:
                    raise ValidationError(
                        "No suitable table is available for the selected timeslot"
                    )
                selected_table_ids = [selected_table_id]
            elif not available_table_repo.validate_table_selection(
                selected_table_id, party_size, start_ts, end_ts
            ):
                raise ValidationError(
                    "Selected table is unavailable for the selected timeslot or party size"
                )
            else:
                selected_table_ids = [selected_table_id]

            max_games = max(1, len(selected_table_ids)) * 2
            if len(games) > max_games:
                raise ValidationError(
                    f"Selected tables allow a maximum number of games of {max_games}"
                )

            booking = CreateBookingRecordUseCase(
                booking_repo=booking_repo,
                table_reservation_repo=table_reservation_repo,
                status_history_repo=status_history_repo,
            ).execute(
                BookingCommand(
                    customer_id=customer_id,
                    table_id=selected_table_id,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    party_size=party_size,
                    notes=notes,
                )
            )
            booking.table_id = selected_table_id
            booking.table_ids = selected_table_ids

            created_games = []
            add_game_use_case = AddGameToReservationUseCase(booking_repo, game_repo)

            for game_request in games:
                requested_game_id = game_request.requested_game_id
                requested_copy_id = game_request.game_copy_id

                if requested_copy_id is None:
                    requested_copy_id = available_copy_repo.find_available_copy_id(
                        requested_game_id, start_ts, end_ts
                    )
                    if requested_copy_id is None:
                        raise ValidationError(
                            f"No available copy for game {requested_game_id} in selected timeslot"
                        )
                else:
                    if not available_copy_repo.validate_copy_available(
                        requested_copy_id, requested_game_id, start_ts, end_ts
                    ):
                        raise ValidationError(
                            "Selected game copy is unavailable for the selected timeslot"
                        )

                created_games.append(
                    add_game_use_case.execute(
                        AddGameToReservationCommand(
                            reservation_id=booking.id,
                            requested_game_id=requested_game_id,
                            game_copy_id=requested_copy_id,
                        )
                    )
                )

            for extra_table_id in selected_table_ids[1:]:
                table_reservation_repo.save(
                    TableReservation(booking_id=booking.id, table_id=extra_table_id)
                )

            billable_booking = type(
                "BillableBooking",
                (),
                {"id": booking.id, "party_size": len(selected_table_ids)},
            )()
            payment = create_and_save_payment(billable_booking, payment_repo)

        return booking, created_games, payment
