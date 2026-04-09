from datetime import datetime

from features.reservations.domain.models.reservation import TableReservation
from features.users.domain.models.user import Role, User
from shared.domain.events import ReservationCreated, UserRegistered
from shared.application.event_handlers.email_event_handler import register_email_event_handlers
from shared.infrastructure import EventBus


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
        self.sent_welcome = []
        self.sent_confirmation = []

    def send_welcome_email(self, recipient_email):
        self.sent_welcome.append(recipient_email)

    def send_reservation_confirmation_email(self, recipient_email, reservation_details):
        self.sent_confirmation.append((recipient_email, reservation_details))


def test_register_email_event_handlers_publishes_to_event_bus():
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
    event_bus = EventBus()

    register_email_event_handlers(event_bus, email_service, reservation_repo, user_repo)

    event_bus.publish(ReservationCreated(reservation_id=1))
    event_bus.publish(UserRegistered(user_id=1, email="ola@example.com"))

    assert email_service.sent_confirmation == [
        (
            "ola@example.com",
            "Table 2, 2026-03-30T18:00:00 to 2026-03-30T20:00:00, party size 4, notes: Bursdag",
        )
    ]
    assert email_service.sent_welcome == ["ola@example.com"]
