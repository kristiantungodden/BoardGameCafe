from datetime import datetime
from datetime import timedelta

from features.bookings.domain.models.booking import Booking
from features.reservations.application.use_cases.steward_reservation_browse_use_cases import (
    BrowseStewardReservationsQuery,
    BrowseStewardReservationsUseCase,
)
from features.users.domain.models.user import User


class FakeReservationRepository:
    def __init__(self, items):
        self._items = list(items)

    def list_all(self):
        return list(self._items)


class FakeUserRepository:
    def __init__(self, users_by_id):
        self._users_by_id = dict(users_by_id)

    def get_by_id(self, user_id):
        return self._users_by_id.get(user_id)


def _reservation(*, rid: int, customer_id: int, status: str, start_ts: datetime):
    reservation = Booking(
        id=rid,
        customer_id=customer_id,
        start_ts=start_ts,
        end_ts=start_ts + timedelta(hours=2),
        party_size=2,
        status=status,
        notes="demo",
    )
    setattr(reservation, "table_id", 1)
    return reservation


def test_browse_steward_reservations_enriches_customer_name_and_email():
    reservations = [
        _reservation(
            rid=1,
            customer_id=10,
            status="confirmed",
            start_ts=datetime(2026, 4, 19, 18, 0),
        )
    ]
    users = {
        10: User(
            id=10,
            name="Alice Guest",
            email="alice@example.com",
            password_hash="hashed",
        )
    }

    use_case = BrowseStewardReservationsUseCase(
        reservation_repo=FakeReservationRepository(reservations),
        user_repo=FakeUserRepository(users),
    )

    result = use_case.execute(BrowseStewardReservationsQuery())

    assert len(result) == 1
    assert result[0].customer_name == "Alice Guest"
    assert result[0].customer_email == "alice@example.com"


def test_browse_steward_reservations_filters_by_status_and_date():
    reservations = [
        _reservation(
            rid=1,
            customer_id=10,
            status="confirmed",
            start_ts=datetime(2026, 4, 19, 18, 0),
        ),
        _reservation(
            rid=2,
            customer_id=20,
            status="seated",
            start_ts=datetime(2026, 4, 19, 19, 0),
        ),
        _reservation(
            rid=3,
            customer_id=30,
            status="confirmed",
            start_ts=datetime(2026, 4, 20, 18, 0),
        ),
    ]

    use_case = BrowseStewardReservationsUseCase(
        reservation_repo=FakeReservationRepository(reservations),
        user_repo=FakeUserRepository({}),
    )

    result = use_case.execute(
        BrowseStewardReservationsQuery(
            statuses=("confirmed",),
            reservation_date=datetime(2026, 4, 19).date(),
        )
    )

    assert [item.id for item in result] == [1]
