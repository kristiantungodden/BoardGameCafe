from datetime import datetime, timedelta, timezone

import pytest

from features.bookings.application.use_cases.booking_lifecycle_use_cases import (
    BookingCommand,
    CancelBookingUseCase,
    CompleteBookingUseCase,
    CreateBookingRecordUseCase,
    SeatBookingUseCase,
)
from features.bookings.domain.models.booking import Booking
from features.payments.domain.models.payment import Payment, PaymentStatus
from features.reservations.domain.models.table_reservation import TableReservation
from features.tables.domain.models.table import Table
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

    def list_by_booking_id(self, booking_id):
        return [item for item in self.items if item.booking_id == booking_id]


class FakeTableRepo:
    def __init__(self):
        self.items = {}

    def get_by_id(self, table_id):
        return self.items.get(table_id)

    def update(self, table):
        self.items[table.id] = table
        return table


class FakeStatusHistoryRepo:
    def __init__(self):
        self.items = []

    def save(self, entry):
        self.items.append(entry)
        return entry

    def list_for_booking(self, booking_id):
        return [item for item in self.items if item.booking_id == booking_id]


class FakePaymentRepo:
    def __init__(self):
        self._payments = {}

    def get_by_booking_id(self, booking_id):
        return self._payments.get(booking_id)

    def update(self, payment):
        self._payments[payment.booking_id] = payment
        return payment


class FakePaymentProvider:
    def __init__(self):
        self.refunded_refs = []

    def refund(self, provider_ref):
        self.refunded_refs.append(provider_ref)
        return True


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
    assert entries[0].to_status == "created"


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


def test_cancel_booking_refunds_paid_stripe_payment():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()
    payment_repo = FakePaymentRepo()
    payment_provider = FakePaymentProvider()

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
    payment_repo._payments[1] = Payment(
        id=101,
        booking_id=1,
        amount_cents=2500,
        provider="stripe",
        provider_ref="cs_test_123",
        status=PaymentStatus.PAID,
    )

    use_case = CancelBookingUseCase(
        booking_repo=booking_repo,
        status_history_repo=history_repo,
        payment_repo=payment_repo,
        payment_provider=payment_provider,
    )

    updated = use_case.execute(1)

    assert updated.status == "cancelled"
    assert payment_provider.refunded_refs == ["cs_test_123"]
    assert payment_repo.get_by_booking_id(1).status == PaymentStatus.REFUNDED


def test_seat_booking_transition_works_without_payment_dependencies():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()
    start = datetime.now(tz=timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)

    booking = Booking(
        id=1,
        customer_id=1,
        start_ts=start,
        end_ts=start + timedelta(hours=2),
        party_size=2,
        status="confirmed",
    )
    booking_repo._items[1] = booking

    use_case = SeatBookingUseCase(
        booking_repo=booking_repo,
        status_history_repo=history_repo,
    )

    updated = use_case.execute(1, actor_user_id=42, actor_role="staff")

    assert updated.status == "seated"
    entries = history_repo.list_for_booking(1)
    assert len(entries) == 1
    assert entries[0].from_status == "confirmed"
    assert entries[0].to_status == "seated"
    assert entries[0].actor_user_id == 42
    assert entries[0].actor_role == "staff"


def test_seat_booking_marks_linked_table_occupied():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()
    table_reservation_repo = FakeTableReservationRepo()
    table_repo = FakeTableRepo()
    start = datetime.now(tz=timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)

    booking = Booking(
        id=1,
        customer_id=1,
        start_ts=start,
        end_ts=start + timedelta(hours=2),
        party_size=2,
        status="confirmed",
    )
    booking_repo._items[1] = booking
    table_reservation_repo.items.append(TableReservation(booking_id=1, table_id=7, id=11))
    table = Table(number=7, capacity=4, status="available")
    table.id = 7
    table_repo.items[7] = table

    use_case = SeatBookingUseCase(
        booking_repo=booking_repo,
        status_history_repo=history_repo,
        table_reservation_repo=table_reservation_repo,
        table_repo=table_repo,
    )

    updated = use_case.execute(1, actor_user_id=42, actor_role="staff")

    assert updated.status == "seated"
    assert table_repo.get_by_id(7).status == "occupied"


def test_seat_booking_rejects_too_early_checkin():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()
    start = datetime.now(tz=timezone.utc).replace(tzinfo=None) + timedelta(minutes=40)

    booking = Booking(
        id=1,
        customer_id=1,
        start_ts=start,
        end_ts=start + timedelta(hours=2),
        party_size=2,
        status="confirmed",
    )
    booking_repo._items[1] = booking

    use_case = SeatBookingUseCase(
        booking_repo=booking_repo,
        status_history_repo=history_repo,
    )

    with pytest.raises(ValidationError, match="15 minutes"):
        use_case.execute(1, actor_user_id=42, actor_role="staff")


def test_complete_booking_frees_linked_table():
    booking_repo = FakeBookingRepo()
    history_repo = FakeStatusHistoryRepo()
    table_reservation_repo = FakeTableReservationRepo()
    table_repo = FakeTableRepo()
    start = datetime.now() + timedelta(days=2)

    booking = Booking(
        id=1,
        customer_id=1,
        start_ts=start,
        end_ts=start + timedelta(hours=2),
        party_size=2,
        status="seated",
    )
    booking_repo._items[1] = booking
    table_reservation_repo.items.append(TableReservation(booking_id=1, table_id=7, id=11))
    table = Table(number=7, capacity=4, status="occupied")
    table.id = 7
    table_repo.items[7] = table

    use_case = CompleteBookingUseCase(
        booking_repo=booking_repo,
        status_history_repo=history_repo,
        table_reservation_repo=table_reservation_repo,
        table_repo=table_repo,
    )

    updated = use_case.execute(1, actor_user_id=42, actor_role="staff")

    assert updated.status == "completed"
    assert table_repo.get_by_id(7).status == "available"
