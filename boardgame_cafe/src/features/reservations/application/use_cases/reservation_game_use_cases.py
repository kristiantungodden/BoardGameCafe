from __future__ import annotations

from dataclasses import dataclass

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.reservations.application.interfaces.game_reservation_repository_interface import (
    GameReservationRepositoryInterface,
)
from features.reservations.domain.models.reservation_game import ReservationGame
from shared.domain.exceptions import ValidationError


_NON_MODIFIABLE_STATUSES = {"cancelled", "completed", "no_show"}


@dataclass
class AddGameToReservationCommand:
    reservation_id: int
    requested_game_id: int
    game_copy_id: int


class AddGameToReservationUseCase:
    def __init__(
        self,
        bookings: BookingRepositoryInterface,
        reservation_games: GameReservationRepositoryInterface,
    ):
        self.bookings = bookings
        self.reservation_games = reservation_games

    def execute(self, cmd: AddGameToReservationCommand) -> ReservationGame:
        booking = self.bookings.get_by_id(cmd.reservation_id)
        if booking is None:
            raise ValidationError("Reservation not found")
        if booking.status in _NON_MODIFIABLE_STATUSES:
            raise ValidationError(
                f"Cannot modify games for reservation in status '{booking.status}'"
            )

        existing = self.reservation_games.list_for_booking(cmd.reservation_id)
        if any(item.game_copy_id == cmd.game_copy_id for item in existing):
            raise ValidationError("Game copy already added to this reservation")

        reservation_game = ReservationGame(
            booking_id=cmd.reservation_id,
            requested_game_id=cmd.requested_game_id,
            game_copy_id=cmd.game_copy_id,
        )
        return self.reservation_games.add(reservation_game)


class RemoveGameFromReservationUseCase:
    def __init__(
        self,
        bookings: BookingRepositoryInterface,
        reservation_games: GameReservationRepositoryInterface,
    ):
        self.bookings = bookings
        self.reservation_games = reservation_games

    def execute(self, reservation_id: int, reservation_game_id: int) -> bool:
        booking = self.bookings.get_by_id(reservation_id)
        if booking is None:
            return False
        if booking.status in _NON_MODIFIABLE_STATUSES:
            raise ValidationError(
                f"Cannot modify games for reservation in status '{booking.status}'"
            )

        reservation_game = self.reservation_games.get_by_id(reservation_game_id)
        if reservation_game is None:
            return False
        if reservation_game.booking_id != reservation_id:
            return False

        return self.reservation_games.delete(reservation_game_id)


class ListReservationGamesUseCase:
    def __init__(
        self,
        bookings: BookingRepositoryInterface,
        reservation_games: GameReservationRepositoryInterface,
    ):
        self.bookings = bookings
        self.reservation_games = reservation_games

    def execute(self, reservation_id: int) -> list[ReservationGame]:
        booking = self.bookings.get_by_id(reservation_id)
        if booking is None:
            raise ValidationError("Reservation not found")
        return list(self.reservation_games.list_for_booking(reservation_id))
