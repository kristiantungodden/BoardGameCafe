from datetime import datetime

from features.reservations.domain.models.reservation import TableReservation
from features.users.domain.models.user import Role, User
from shared.application.event_handlers.email_event_handler import (
    send_reservation_confirmation_email,
)
from shared.domain.events import ReservationCreated


class FakeReservationRepo:
    def __init__(self, reservation):
        self.reservation = reservation

    def get_by_id(self, reservation_id):
        if self.reservation.id == reservation_id:
            return self.reservation
        return None


class FakeUserRepo:
    def __init__(self, user):
        self.user = user

    def get_by_id(self, user_id):
        if self.user.id == user_id:
            return self.user
        return None


class DummyEmailService:
    def __init__(self):
        self.sent = []

    def send_reservation_confirmation_email(self, recipient_email, reservation_details):
        self.sent.append((recipient_email, reservation_details))


def test_send_reservation_confirmation_email_loads_related_data():
    reservation = TableReservation(
        customer_id=1,
        table_id=2,
        start_ts=datetime(2026, 3, 30, 18, 0),
        end_ts=datetime(2026, 3, 30, 20, 0),
        party_size=4,
        notes="Bursdag",
    )
    reservation.id = 1

    user = User(
        name="Ola Nordmann",
        email="ola@example.com",
        password_hash="hash",
        role=Role.CUSTOMER,
        phone="12345678",
    )
    user.id = 1

    reservation_repo = FakeReservationRepo(reservation)
    user_repo = FakeUserRepo(user)
    email_service = DummyEmailService()

    event = ReservationCreated(reservation_id=1)
    send_reservation_confirmation_email(event, email_service, reservation_repo, user_repo)

    assert email_service.sent == [
        (
            "ola@example.com",
            "Table 2, 2026-03-30T18:00:00 to 2026-03-30T20:00:00, party size 4, notes: Bursdag",
        )
    ]
