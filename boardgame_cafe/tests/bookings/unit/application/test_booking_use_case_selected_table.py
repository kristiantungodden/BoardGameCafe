from datetime import datetime

import pytest

import features.bookings.application.use_cases.booking_use_cases as booking_module
from features.bookings.application.use_cases.booking_use_cases import CreateBookingUseCase
from shared.domain.exceptions import ValidationError


class FakeBookingRepo:
    _next_id = 1

    def __init__(self, session=None, auto_commit=True):
        self._items = []

    def save(self, booking):
        booking.id = FakeBookingRepo._next_id
        FakeBookingRepo._next_id += 1
        self._items.append(booking)
        return booking

    def get_by_id(self, booking_id):
        return next((b for b in self._items if b.id == booking_id), None)

    def list_all(self):
        return list(self._items)

    def update(self, booking):
        return booking

    def list_by_customer(self, customer_id):
        return [item for item in self._items if item.customer_id == customer_id]

    def find_overlapping_bookings(self, customer_id, start_ts, end_ts, statuses):
        return []


class FakeTableReservationRepo:
    def __init__(self, session=None, auto_commit=True):
        self.links = []

    def save(self, table_reservation):
        self.links.append(table_reservation)
        return table_reservation


class FakeGameRepo:
    def __init__(self, session=None, auto_commit=True):
        pass


class FakeAvailableTableRepo:
    should_validate = True

    def __init__(self, session=None):
        pass

    def find_best_available_table(self, party_size, start_ts, end_ts):
        return 1

    def validate_table_selection(self, table_id, party_size, start_ts, end_ts):
        return FakeAvailableTableRepo.should_validate


class FakeAvailableCopyRepo:
    def __init__(self, session=None):
        pass

    def find_available_copy_id(self, game_id, start_ts, end_ts):
        return 1

    def validate_copy_available(self, game_copy_id, game_id, start_ts, end_ts):
        return True


class DummyPayment:
    id = 1


def _stub_create_and_save_payment(booking, payment_repo):
    return DummyPayment()


def test_create_booking_rejects_unavailable_selected_table(app, monkeypatch):
    FakeAvailableTableRepo.should_validate = False
    monkeypatch.setattr(booking_module, "create_and_save_payment", _stub_create_and_save_payment)

    use_case = CreateBookingUseCase(
        booking_repo=FakeBookingRepo(),
        table_reservation_repo=FakeTableReservationRepo(),
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
        booking_repo=FakeBookingRepo(),
        table_reservation_repo=FakeTableReservationRepo(),
        game_repo=FakeGameRepo(),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        booking, created_games, payment = use_case.execute(
            customer_id=1,
            table_id=7,
            start_ts=datetime(2026, 4, 10, 18, 0),
            end_ts=datetime(2026, 4, 10, 20, 0),
            party_size=4,
            games=[],
        )

    assert booking.id is not None
    assert booking.customer_id == 1
    assert booking.party_size == 4
    assert created_games == []
    assert payment.id == 1
