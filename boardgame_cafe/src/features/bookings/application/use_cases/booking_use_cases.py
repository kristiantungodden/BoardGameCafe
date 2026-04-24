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
from features.games.application.interfaces.game_repository_interface import (
    GameRepositoryInterface,
)
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
from features.tables.application.interfaces.table_repository import (
    TableRepository as TableRepositoryInterface,
)
from shared.domain.exceptions import ValidationError


@dataclass
class BookingGameRequest:
    requested_game_id: int
    game_copy_id: Optional[int] = None


DEFAULT_BASE_FEE_CENTS = 2500


class CreateBookingUseCase:
    def __init__(
        self,
        booking_repo,
        table_reservation_repo,
        game_repo,
        table_repo: TableRepositoryInterface,
        game_lookup_repo: GameRepositoryInterface,
        available_table_repo: AvailableTableRepositoryInterface,
        available_copy_repo: AvailableGameCopyRepositoryInterface,
        payment_repo: PaymentRepositoryInterface,
        status_history_repo: BookingStatusHistoryRepositoryInterface | None = None,
    ):
        self.booking_repo = booking_repo
        self.table_reservation_repo = table_reservation_repo
        self.game_repo = game_repo
        self.table_repo = table_repo
        self.game_lookup_repo = game_lookup_repo
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
        base_fee_cents: int | None = None,
    ):
        selected_table_ids = list(dict.fromkeys(table_ids or []))

        selected_table_id = table_id
        if selected_table_ids:
            if selected_table_id is not None and selected_table_id not in selected_table_ids:
                selected_table_ids.insert(0, selected_table_id)

            selected_tables = []
            for selected_id in selected_table_ids:
                if not self.available_table_repo.validate_table_selection(
                    selected_id, 1, start_ts, end_ts
                ):
                    raise ValidationError(
                        "One or more selected tables are unavailable for the selected timeslot"
                    )

                table = self.table_repo.get_by_id(selected_id)
                if table is None:
                    raise ValidationError(
                        "One or more selected tables are unavailable for the selected timeslot"
                    )
                selected_tables.append(table)

            total_capacity = sum(int(getattr(row, "capacity", 0) or 0) for row in selected_tables)
            if total_capacity < party_size:
                raise ValidationError(
                    "Selected tables do not provide enough combined capacity for the party size"
                )
            selected_table_id = selected_table_ids[0]
        elif selected_table_id is None:
            selected_table_id = self.available_table_repo.find_best_available_table(
                party_size, start_ts, end_ts
            )
            if selected_table_id is None:
                raise ValidationError("No suitable table is available for the selected timeslot")
            selected_table_ids = [selected_table_id]
        elif not self.available_table_repo.validate_table_selection(
            selected_table_id, party_size, start_ts, end_ts
        ):
            raise ValidationError(
                "Selected table is unavailable for the selected timeslot or party size"
            )
        else:
            selected_table_ids = [selected_table_id]

        max_games = max(1, len(selected_table_ids)) * 2
        if len(games) > max_games:
            raise ValidationError(f"Selected tables allow a maximum number of games of {max_games}")

        booking = CreateBookingRecordUseCase(
            booking_repo=self.booking_repo,
            table_reservation_repo=self.table_reservation_repo,
            status_history_repo=self.status_history_repo,
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
        add_game_use_case = AddGameToReservationUseCase(self.booking_repo, self.game_repo)

        for game_request in games:
            requested_game_id = game_request.requested_game_id
            requested_copy_id = game_request.game_copy_id

            if requested_copy_id is None:
                requested_copy_id = self.available_copy_repo.find_available_copy_id(
                    requested_game_id, start_ts, end_ts
                )
                if requested_copy_id is None:
                    raise ValidationError(
                        f"No available copy for game {requested_game_id} in selected timeslot"
                    )
            else:
                if not self.available_copy_repo.validate_copy_available(
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
            self.table_reservation_repo.save(
                TableReservation(booking_id=booking.id, table_id=extra_table_id)
            )

        table_price_total = 0
        if selected_table_ids:
            table_rows = [self.table_repo.get_by_id(table_id) for table_id in selected_table_ids]
            table_price_total = sum(int(getattr(row, "price_cents", 0) or 0) for row in table_rows if row)

        requested_game_ids = [item.requested_game_id for item in created_games]
        game_price_total = 0
        if requested_game_ids:
            game_rows = [self.game_lookup_repo.get_game(game_id) for game_id in requested_game_ids]
            game_price_total = sum(int(getattr(row, "price_cents", 0) or 0) for row in game_rows if row)

        fee_cents = DEFAULT_BASE_FEE_CENTS if base_fee_cents is None else int(base_fee_cents)

        billable_booking = type(
            "BillableBooking",
            (),
            {
                "id": booking.id,
                "party_size": len(selected_table_ids),
                "table_price_cents_total": table_price_total,
                "game_price_cents_total": game_price_total,
                "base_fee_cents": fee_cents,
            },
        )()
        payment = create_and_save_payment(billable_booking, self.payment_repo)

        return booking, created_games, payment
