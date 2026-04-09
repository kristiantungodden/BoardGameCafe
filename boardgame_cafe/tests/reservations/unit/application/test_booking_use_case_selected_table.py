from datetime import datetime

import pytest

import features.reservations.application.use_cases.booking_use_cases as booking_module
from features.reservations.application.use_cases.booking_use_cases import CreateBookingUseCase
from shared.domain.exceptions import ValidationError


class FakeReservationRepo:
    _next_id = 1

    def __init__(self, session=None, auto_commit=True):
        self._items = []

    def add(self, reservation):
        reservation.id = FakeReservationRepo._next_id
        FakeReservationRepo._next_id += 1
        self._items.append(reservation)
        return reservation

    def get_by_id(self, reservation_id):
        return next((r for r in self._items if r.id == reservation_id), None)

    def list_all(self):
        return list(self._items)

    def list_for_table_in_window(self, table_id, start_ts, end_ts):
        return [
            item
            for item in self._items
            if item.table_id == table_id and item.start_ts < end_ts and start_ts < item.end_ts
        ]

    def update(self, reservation):
        return reservation


class FakeGameRepo:
    def __init__(self, session=None, auto_commit=True):
        pass


class FakeAvailableTableRepo:
    should_validate = True
    best_table_id = 1

    def __init__(self, session=None):
        pass

    def get_blocked_table_ids(self, start_ts, end_ts):
        return set()

    def find_best_available_table(self, party_size, start_ts, end_ts):
        return FakeAvailableTableRepo.best_table_id

    def validate_table_selection(self, table_id, party_size, start_ts, end_ts):
        return FakeAvailableTableRepo.should_validate


class FakeAvailableCopyRepo:
    def __init__(self, session=None):
        pass

    def get_blocked_copy_ids(self, start_ts, end_ts):
        return set()

    def find_available_copy_id(self, game_id, start_ts, end_ts):
        return 1

    def validate_copy_available(self, game_copy_id, game_id, start_ts, end_ts):
        return True


class DummyPayment:
    id = 1


def _stub_create_and_save_payment(reservation, payment_repo):
    return DummyPayment()


def test_create_booking_rejects_unavailable_selected_table(app, monkeypatch):
    FakeAvailableTableRepo.should_validate = False
    monkeypatch.setattr(booking_module, "create_and_save_payment", _stub_create_and_save_payment)

    use_case = CreateBookingUseCase(
        reservation_repo=FakeReservationRepo(),
        game_repo=FakeGameRepo(),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        with pytest.raises(ValidationError, match="Selected table is unavailable"):
            use_case.execute(
                customer_id=1,
                table_id=7,
                start_ts=datetime(2026, 4, 10, 18, 0),
                end_ts=datetime(2026, 4, 10, 20, 0),
                party_size=4,
                games=[],
            )


def test_create_booking_accepts_valid_selected_table(app, monkeypatch):
    FakeAvailableTableRepo.should_validate = True
    monkeypatch.setattr(booking_module, "create_and_save_payment", _stub_create_and_save_payment)

    use_case = CreateBookingUseCase(
        reservation_repo=FakeReservationRepo(),
        game_repo=FakeGameRepo(),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        reservation, created_games, payment = use_case.execute(
            customer_id=1,
            table_id=7,
            start_ts=datetime(2026, 4, 10, 18, 0),
            end_ts=datetime(2026, 4, 10, 20, 0),
            party_size=4,
            games=[],
        )

    assert reservation.table_id == 7
    assert created_games == []
    assert payment.id == 1
