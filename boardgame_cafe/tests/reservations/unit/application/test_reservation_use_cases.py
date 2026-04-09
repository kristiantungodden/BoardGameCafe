from datetime import datetime

from features.reservations.application.use_cases.reservation_use_cases import (
    CancelReservationUseCase,
    CompleteReservationUseCase,
    CreateReservationCommand,
    CreateReservationUseCase,
    MarkReservationNoShowUseCase,
    SeatReservationUseCase,
)
from features.bookings.domain.models.booking import Booking
from shared.domain.exceptions import ValidationError


def _make_reservation(*, table_id: int, **kwargs) -> Booking:
    reservation = Booking(**kwargs)
    setattr(reservation, "table_id", table_id)
    return reservation


class FakeReservationRepo:
    def __init__(self):
        self.items = []
        self.next_id = 1

    def add(self, reservation):
        reservation.id = self.next_id
        self.next_id += 1
        self.items.append(reservation)
        return reservation

    def get_by_id(self, reservation_id):
        for item in self.items:
            if item.id == reservation_id:
                return item
        return None

    def list_all(self):
        return self.items

    def list_for_table_in_window(self, table_id, start_ts, end_ts):
        return [
            r for r in self.items
            if r.table_id == table_id and r.start_ts < end_ts and start_ts < r.end_ts
        ]

    def update(self, reservation):
        return reservation


def test_create_reservation_from_customer_order():
    repo = FakeReservationRepo()
    use_case = CreateReservationUseCase(repo)

    cmd = CreateReservationCommand(
        customer_id=1,
        table_id=2,
        start_ts=datetime(2026, 3, 30, 18, 0),
        end_ts=datetime(2026, 3, 30, 20, 0),
        party_size=4,
        notes="Bursdag",
    )

    reservation = use_case.execute(cmd)

    assert reservation.id == 1
    assert reservation.customer_id == 1
    assert reservation.table_id == 2
    assert reservation.party_size == 4
    assert reservation.notes == "Bursdag"
    assert reservation.status == "confirmed"


def test_cancel_reservation_use_case_updates_status():
    repo = FakeReservationRepo()
    created = CreateReservationUseCase(repo).execute(
        CreateReservationCommand(
            customer_id=1,
            table_id=2,
            start_ts=datetime(2026, 3, 30, 18, 0),
            end_ts=datetime(2026, 3, 30, 20, 0),
            party_size=4,
        )
    )
    use_case = CancelReservationUseCase(repo)

    updated = use_case.execute(created.id)

    assert updated is not None
    assert updated.status == "cancelled"


def test_seat_and_complete_reservation_use_case_updates_status():
    repo = FakeReservationRepo()
    created = CreateReservationUseCase(repo).execute(
        CreateReservationCommand(
            customer_id=1,
            table_id=2,
            start_ts=datetime(2026, 3, 30, 18, 0),
            end_ts=datetime(2026, 3, 30, 20, 0),
            party_size=4,
        )
    )

    seated = SeatReservationUseCase(repo).execute(created.id)
    assert seated is not None
    assert seated.status == "seated"

    completed = CompleteReservationUseCase(repo).execute(created.id)

    assert completed is not None
    assert completed.status == "completed"


def test_mark_no_show_reservation_use_case_updates_status():
    repo = FakeReservationRepo()
    created = CreateReservationUseCase(repo).execute(
        CreateReservationCommand(
            customer_id=1,
            table_id=2,
            start_ts=datetime(2026, 3, 30, 18, 0),
            end_ts=datetime(2026, 3, 30, 20, 0),
            party_size=4,
        )
    )

    updated = MarkReservationNoShowUseCase(repo).execute(created.id)

    assert updated is not None
    assert updated.status == "no_show"


def test_create_reservation_rejects_overlap_with_confirmed_reservation():
    repo = FakeReservationRepo()
    repo.items.append(
        _make_reservation(
            id=99,
            customer_id=2,
            table_id=2,
            start_ts=datetime(2026, 3, 30, 18, 30),
            end_ts=datetime(2026, 3, 30, 19, 30),
            party_size=2,
            status="confirmed",
        )
    )
    use_case = CreateReservationUseCase(repo)

    try:
        use_case.execute(
            CreateReservationCommand(
                customer_id=1,
                table_id=2,
                start_ts=datetime(2026, 3, 30, 18, 0),
                end_ts=datetime(2026, 3, 30, 20, 0),
                party_size=4,
            )
        )
        assert False, "Expected ValidationError"
    except ValidationError:
        assert True


def test_create_reservation_allows_overlap_with_cancelled_reservation():
    repo = FakeReservationRepo()
    repo.items.append(
        _make_reservation(
            id=98,
            customer_id=2,
            table_id=2,
            start_ts=datetime(2026, 3, 30, 18, 30),
            end_ts=datetime(2026, 3, 30, 19, 30),
            party_size=2,
            status="cancelled",
        )
    )
    use_case = CreateReservationUseCase(repo)

    reservation = use_case.execute(
        CreateReservationCommand(
            customer_id=1,
            table_id=2,
            start_ts=datetime(2026, 3, 30, 18, 0),
            end_ts=datetime(2026, 3, 30, 20, 0),
            party_size=4,
        )
    )

    assert reservation.id is not None
    assert reservation.status == "confirmed"


def test_create_reservation_rejects_overnight_booking():
    repo = FakeReservationRepo()
    use_case = CreateReservationUseCase(repo)

    try:
        use_case.execute(
            CreateReservationCommand(
                customer_id=1,
                table_id=2,
                start_ts=datetime(2026, 3, 30, 22, 0),
                end_ts=datetime(2026, 3, 31, 1, 0),
                party_size=4,
            )
        )
        assert False, "Expected ValidationError"
    except ValidationError as exc:
        assert "no overnight" in str(exc).lower()


def test_create_reservation_rejects_outside_opening_hours():
    repo = FakeReservationRepo()
    use_case = CreateReservationUseCase(repo)

    try:
        use_case.execute(
            CreateReservationCommand(
                customer_id=1,
                table_id=2,
                start_ts=datetime(2026, 3, 30, 8, 30),
                end_ts=datetime(2026, 3, 30, 10, 0),
                party_size=2,
            )
        )
        assert False, "Expected ValidationError"
    except ValidationError as exc:
        assert "opening hours" in str(exc).lower()