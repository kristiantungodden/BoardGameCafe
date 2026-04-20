from datetime import datetime, timedelta

import pytest

from features.bookings.application.use_cases.booking_lifecycle_use_cases import (
    BookingCommand,
    CancelBookingUseCase,
    CreateBookingRecordUseCase,
)
from features.bookings.domain.models.booking import Booking
from shared.domain.exceptions import InvalidStatusTransition, ValidationError


class FakeBookingRepo:
    def __init__(self):
        self._items = {}
        self._next_id = 1

    def save(self, booking):
        booking.id = self._next_id
        self._next_id += 1
        self._items[booking.id] = booking
        return booking

    def update(self, booking):
        self._items[booking.id] = booking
        return booking

    def get_by_id(self, booking_id):
        return self._items.get(booking_id)

    def find_overlapping_bookings(self, customer_id, start_ts, end_ts, statuses):
        return []


class FakeTableReservationRepo:
    def __init__(self):
        self.items = []

    def save(self, table_reservation):
        self.items.append(table_reservation)
        return table_reservation


class FakeStatusHistoryRepo:
    def __init__(self):
        self.items = []

    def save(self, entry):
        self.items.append(entry)
        return entry

    def list_for_booking(self, booking_id):
        return [item for item in self.items if item.booking_id == booking_id]


def test_create_booking_records_initial_status_history():
    booking_repo = FakeBookingRepo()
    table_repo = FakeTableReservationRepo()
    history_repo = FakeStatusHistoryRepo()

    use_case = CreateBookingRecordUseCase(
        booking_repo=booking_repo,
        table_reservation_repo=table_repo,
        status_history_repo=history_repo,
    )

    created = use_case.execute(
        BookingCommand(
            customer_id=1,
            table_id=2,
            start_ts=datetime(2026, 4, 20, 18, 0),
            end_ts=datetime(2026, 4, 20, 20, 0),
            party_size=4,
        )
    )

    entries = history_repo.list_for_booking(created.id)
    assert len(entries) == 1
    assert entries[0].from_status is None
    assert entries[0].to_status == "confirmed"


def test_cancel_booking_records_status_history_transition():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()

    start = datetime.now() + timedelta(days=2)

    booking = Booking(
        id=1,
        customer_id=1,
        start_ts=start,
        end_ts=start + timedelta(hours=2),
        party_size=4,
        status="confirmed",
    )
    booking_repo._items[1] = booking

    use_case = CancelBookingUseCase(booking_repo=booking_repo, status_history_repo=history_repo)
    updated = use_case.execute(1, actor_user_id=99, actor_role="customer")

    assert updated.status == "cancelled"
    entries = history_repo.list_for_booking(1)
    assert len(entries) == 1
    assert entries[0].from_status == "confirmed"
    assert entries[0].to_status == "cancelled"
    assert entries[0].actor_user_id == 99
    assert entries[0].actor_role == "customer"


def test_invalid_transition_does_not_record_status_history():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()

    start = datetime.now() + timedelta(days=2)

    booking = Booking(
        id=1,
        customer_id=1,
        start_ts=start,
        end_ts=start + timedelta(hours=2),
        party_size=4,
        status="seated",
    )
    booking_repo._items[1] = booking

    use_case = CancelBookingUseCase(booking_repo=booking_repo, status_history_repo=history_repo)

    with pytest.raises(InvalidStatusTransition):
        use_case.execute(1)

    assert history_repo.list_for_booking(1) == []


def test_cancel_booking_requires_24h_notice():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()

    start = datetime.now() + timedelta(hours=23)
    booking = Booking(
        id=1,
        customer_id=1,
        start_ts=start,
        end_ts=start + timedelta(hours=2),
        party_size=2,
        status="confirmed",
    )
    booking_repo._items[1] = booking

    use_case = CancelBookingUseCase(booking_repo=booking_repo, status_history_repo=history_repo)

    with pytest.raises(ValidationError, match="24 hours"):
        use_case.execute(1)

    assert booking_repo.get_by_id(1).status == "confirmed"
    assert history_repo.list_for_booking(1) == []
