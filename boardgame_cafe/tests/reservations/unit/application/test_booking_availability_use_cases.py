from datetime import datetime
from types import SimpleNamespace

from features.reservations.application.use_cases.booking_availability_use_cases import (
    GetBookingAvailabilityUseCase,
)


class _FakeAvailableTableRepo:
    def find_best_available_table(self, party_size, start_ts, end_ts):
        return 42


class _FakeAvailableCopyRepo:
    def get_blocked_copy_ids(self, start_ts, end_ts):
        return {2}


class _FakeTableRepo:
    def get_by_id(self, table_id):
        return SimpleNamespace(
            id=table_id,
            table_nr="T42",
            capacity=4,
            status="available",
        )


class _FakeGameCopyRepo:
    def list_all(self):
        return [
            SimpleNamespace(id=1, game_id=10),
            SimpleNamespace(id=2, game_id=20),
        ]


class _FakeGameRepo:
    def get_all_games(self):
        return [
            SimpleNamespace(id=10, title="Catan", price_cents=7900),
            SimpleNamespace(id=20, title="UNO", price_cents=1800),
            SimpleNamespace(id=30, title="Chess", price_cents=3100),
        ]


def test_booking_availability_returns_all_games_with_slot_availability():
    use_case = GetBookingAvailabilityUseCase(
        available_table_repo=_FakeAvailableTableRepo(),
        available_copy_repo=_FakeAvailableCopyRepo(),
        table_repo=_FakeTableRepo(),
        game_copy_repo=_FakeGameCopyRepo(),
        game_repo=_FakeGameRepo(),
    )

    result = use_case.execute(
        datetime(2026, 4, 25, 18, 0),
        datetime(2026, 4, 25, 20, 0),
        4,
    )

    assert result["suggested_table"]["id"] == 42
    assert result["games"] == [
        {
            "id": 10,
            "title": "Catan",
            "price_cents": 7900,
            "available": True,
            "suggested_copy_id": 1,
        },
        {
            "id": 20,
            "title": "UNO",
            "price_cents": 1800,
            "available": False,
            "suggested_copy_id": None,
        },
        {
            "id": 30,
            "title": "Chess",
            "price_cents": 3100,
            "available": False,
            "suggested_copy_id": None,
        },
    ]
