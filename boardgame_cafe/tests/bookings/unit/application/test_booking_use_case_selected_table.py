from datetime import datetime

import pytest

import features.bookings.application.use_cases.booking_use_cases as booking_module
from features.bookings.application.use_cases.booking_use_cases import CreateBookingUseCase
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.tables.infrastructure.database.table_db import TableDB
from features.tables.infrastructure.repositories.table_repository import (
    TableRepository as SqlAlchemyTableRepository,
)
from shared.infrastructure import db
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
    links = []

    def __init__(self, session=None, auto_commit=True):
        pass

    def save(self, table_reservation):
        FakeTableReservationRepo.links.append(table_reservation)
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


def _create_test_table(table_nr: str, capacity: int) -> int:
    table = TableDB(
        table_nr=table_nr,
        capacity=capacity,
        floor=1,
        zone="Test",
        status="available",
    )
    db.session.add(table)
    db.session.commit()
    return table.id


class _FakeAddGameUseCase:
    def __init__(self, bookings, reservation_games):
        self._next_id = 1

    def execute(self, cmd):
        item = type(
            "ReservationGame",
            (),
            {
                "id": self._next_id,
                "booking_id": cmd.reservation_id,
                "requested_game_id": cmd.requested_game_id,
                "game_copy_id": cmd.game_copy_id,
            },
        )()
        self._next_id += 1
        return item


def test_create_booking_rejects_unavailable_selected_table(app, monkeypatch):
    FakeAvailableTableRepo.should_validate = False
    monkeypatch.setattr(booking_module, "create_and_save_payment", _stub_create_and_save_payment)

    use_case = CreateBookingUseCase(
        booking_repo=FakeBookingRepo(),
        table_reservation_repo=FakeTableReservationRepo(),
        game_repo=FakeGameRepo(),
        table_repo=SqlAlchemyTableRepository(session=db.session),
        game_lookup_repo=GameRepository(session=db.session),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        selected_table_id = _create_test_table("UT-1", 4)
        with pytest.raises(ValidationError, match="Selected table is unavailable"):
            use_case.execute(
                customer_id=1,
                table_id=selected_table_id,
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
        table_repo=SqlAlchemyTableRepository(session=db.session),
        game_lookup_repo=GameRepository(session=db.session),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        selected_table_id = _create_test_table("UT-2", 4)
        booking, created_games, payment = use_case.execute(
            customer_id=1,
            table_id=selected_table_id,
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


def test_create_booking_rejects_more_than_two_games_per_selected_table(app, monkeypatch):
    FakeAvailableTableRepo.should_validate = True
    monkeypatch.setattr(booking_module, "create_and_save_payment", _stub_create_and_save_payment)

    use_case = CreateBookingUseCase(
        booking_repo=FakeBookingRepo(),
        table_reservation_repo=FakeTableReservationRepo(),
        game_repo=FakeGameRepo(),
        table_repo=SqlAlchemyTableRepository(session=db.session),
        game_lookup_repo=GameRepository(session=db.session),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        selected_table_id = _create_test_table("UT-3", 4)
        with pytest.raises(ValidationError, match="maximum number of games"):
            use_case.execute(
                customer_id=1,
                table_id=selected_table_id,
                start_ts=datetime(2026, 4, 10, 18, 0),
                end_ts=datetime(2026, 4, 10, 20, 0),
                party_size=4,
                games=[
                    booking_module.BookingGameRequest(requested_game_id=1),
                    booking_module.BookingGameRequest(requested_game_id=2),
                    booking_module.BookingGameRequest(requested_game_id=3),
                ],
            )


def test_create_booking_allows_two_games_per_table_across_multiple_tables(app, monkeypatch):
    FakeAvailableTableRepo.should_validate = True
    FakeTableReservationRepo.links = []
    monkeypatch.setattr(booking_module, "create_and_save_payment", _stub_create_and_save_payment)
    monkeypatch.setattr(booking_module, "AddGameToReservationUseCase", _FakeAddGameUseCase)

    use_case = CreateBookingUseCase(
        booking_repo=FakeBookingRepo(),
        table_reservation_repo=FakeTableReservationRepo(),
        game_repo=FakeGameRepo(),
        table_repo=SqlAlchemyTableRepository(session=db.session),
        game_lookup_repo=GameRepository(session=db.session),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        table_one_id = _create_test_table("UT-4", 4)
        table_two_id = _create_test_table("UT-5", 6)
        booking, created_games, _ = use_case.execute(
            customer_id=1,
            table_id=None,
            table_ids=[table_one_id, table_two_id],
            start_ts=datetime(2026, 4, 10, 18, 0),
            end_ts=datetime(2026, 4, 10, 20, 0),
            party_size=10,
            games=[
                booking_module.BookingGameRequest(requested_game_id=1),
                booking_module.BookingGameRequest(requested_game_id=2),
                booking_module.BookingGameRequest(requested_game_id=3),
                booking_module.BookingGameRequest(requested_game_id=4),
            ],
        )

    assert booking.id is not None
    assert booking.table_id == table_one_id
    assert booking.table_ids == [table_one_id, table_two_id]
    assert len(created_games) == 4
    assert len(FakeTableReservationRepo.links) == 2


def test_create_booking_rejects_multiple_tables_when_combined_capacity_too_small(app, monkeypatch):
    FakeAvailableTableRepo.should_validate = True
    monkeypatch.setattr(booking_module, "create_and_save_payment", _stub_create_and_save_payment)

    use_case = CreateBookingUseCase(
        booking_repo=FakeBookingRepo(),
        table_reservation_repo=FakeTableReservationRepo(),
        game_repo=FakeGameRepo(),
        table_repo=SqlAlchemyTableRepository(session=db.session),
        game_lookup_repo=GameRepository(session=db.session),
        available_table_repo=FakeAvailableTableRepo(),
        available_copy_repo=FakeAvailableCopyRepo(),
        payment_repo=None,
    )

    with app.app_context():
        table_one_id = _create_test_table("UT-6", 2)
        table_two_id = _create_test_table("UT-7", 2)

        with pytest.raises(ValidationError, match="combined capacity"):
            use_case.execute(
                customer_id=1,
                table_id=table_one_id,
                table_ids=[table_one_id, table_two_id],
                start_ts=datetime(2026, 4, 10, 18, 0),
                end_ts=datetime(2026, 4, 10, 20, 0),
                party_size=5,
                games=[],
            )
