"""Register email-related async task subscriptions for domain events."""

from shared.application.interface import EmailServiceInterface
from shared.domain.events import (
    ReservationCreated,
    ReservationPaymentCompleted,
    UserRegistered,
)

# Denne modulen subber bare
def register_email_event_handlers(event_bus, _email_service: EmailServiceInterface):
    # Async handlers via Celery for pub/sub style event processing.
    event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")
    event_bus.subscribe_task(
        ReservationPaymentCompleted,
        "shared.tasks.send_reservation_confirmation_email",
    )
    event_bus.subscribe_task(UserRegistered, "shared.tasks.publish_realtime_event")
    event_bus.subscribe_task(ReservationCreated, "shared.tasks.publish_realtime_event")