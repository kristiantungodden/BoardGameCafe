from datetime import datetime

from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationCommand,
    AddGameToReservationUseCase,
    RemoveGameFromReservationUseCase,
)
from features.reservations.domain.models.reservation import TableReservation
from features.reservations.domain.models.reservation_game import ReservationGame
from shared.domain.exceptions import ValidationError


class FakeReservationRepo:
    def __init__(self):
        self.reservations = {
            1: TableReservation(
                id=1,
                customer_id=1,
                table_id=2,
                start_ts=datetime(2026, 3, 30, 18, 0),
                end_ts=datetime(2026, 3, 30, 20, 0),
                party_size=4,
                status="confirmed",
            )
        }

    def get_by_id(self, reservation_id):
        return self.reservations.get(reservation_id)


class FakeReservationGameRepo:
    def __init__(self):
        self.items = []
        self.next_id = 1

    def add(self, reservation_game):
        reservation_game.id = self.next_id
        self.next_id += 1
        self.items.append(reservation_game)
        return reservation_game

    def get_by_id(self, reservation_game_id):
        for item in self.items:
            if item.id == reservation_game_id:
                return item
        return None

    def list_for_reservation(self, reservation_id):
        return [item for item in self.items if item.table_reservation_id == reservation_id]

    def delete(self, reservation_game_id):
        item = self.get_by_id(reservation_game_id)
        if item is None:
            return False
        self.items.remove(item)
        return True


def test_add_game_to_reservation_success():
    reservation_repo = FakeReservationRepo()
    game_repo = FakeReservationGameRepo()
    use_case = AddGameToReservationUseCase(reservation_repo, game_repo)

    result = use_case.execute(
        AddGameToReservationCommand(
            reservation_id=1,
            requested_game_id=3,
            game_copy_id=7,
        )
    )

    assert result.id == 1
    assert result.table_reservation_id == 1
    assert result.requested_game_id == 3
    assert result.game_copy_id == 7


def test_add_game_to_reservation_rejects_duplicate_copy():
    reservation_repo = FakeReservationRepo()
    game_repo = FakeReservationGameRepo()
    game_repo.add(
        ReservationGame(
            table_reservation_id=1,
            requested_game_id=2,
            game_copy_id=7,
        )
    )
    use_case = AddGameToReservationUseCase(reservation_repo, game_repo)

    try:
        use_case.execute(
            AddGameToReservationCommand(
                reservation_id=1,
                requested_game_id=3,
                game_copy_id=7,
            )
        )
        assert False, "Expected ValidationError"
    except ValidationError:
        assert True


def test_remove_game_from_reservation_success():
    reservation_repo = FakeReservationRepo()
    game_repo = FakeReservationGameRepo()
    saved = game_repo.add(
        ReservationGame(
            table_reservation_id=1,
            requested_game_id=2,
            game_copy_id=7,
        )
    )

    use_case = RemoveGameFromReservationUseCase(reservation_repo, game_repo)

    removed = use_case.execute(1, saved.id)

    assert removed is True
    assert game_repo.get_by_id(saved.id) is None
