from shared.domain.events import ReservationCreated
from shared.infrastructure.email.event_bus import EventBus


class FakeCelery:
    def __init__(self):
        self.calls = []

    def send_task(self, task_name, kwargs, retry=False):
        self.calls.append((task_name, kwargs, retry))


def test_event_bus_dispatches_subscribed_task(monkeypatch):
    fake_celery = FakeCelery()
    monkeypatch.setattr("shared.infrastructure.email.event_bus.celery", fake_celery)

    event_bus = EventBus()
    event_bus.subscribe_task(
        ReservationCreated,
        "shared.tasks.send_reservation_confirmation_email",
    )

    event_bus.publish(
        ReservationCreated(
            reservation_id=10,
            user_id=7,
            user_email="user@example.com",
            reservation_details="Reservation #10",
        )
    )

    assert len(fake_celery.calls) == 1
    task_name, kwargs, retry = fake_celery.calls[0]
    assert task_name == "shared.tasks.send_reservation_confirmation_email"
    assert retry is False
    payload = kwargs["event_payload"]
    assert payload["event_type"] == "ReservationCreated"
    assert payload["data"]["user_email"] == "user@example.com"
