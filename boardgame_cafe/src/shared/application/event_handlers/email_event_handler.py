#Her skal vi koble domain og infrastructure sammen for å sende email når en reservasjon er laget eller en bruker har registrert seg.
from shared.application.interface import EmailServiceInterface
from shared.domain.events import UserRegistered, ReservationCreated

def send_welcome_email(event: UserRegistered, email_service: EmailServiceInterface):
    email_service.send_welcome_email(event.email)

def send_reservation_confirmation_email(event: ReservationCreated, email_service: EmailServiceInterface):
    # For DDD er det bedre at eventet inneholder all data som trengs for å håndtere det.
    # Derfor bør reservation use case legge ved user_email når ReservationCreated publiseres.
    details = (
        f"table_numbers={event.table_numbers}, start_ts={event.start_ts}, "
        f"end_ts={event.end_ts}, party_size={event.party_size}"
    )
    email_service.send_email(
        subject="Your Dicer.no Reservation Confirmation",
        sender=None,
        recipients=[event.user_email],
        body=(
            "Thank you for your reservation at Dicer.no! \n\n"
            f"Here are your reservation details:\n{details}\n\n"
            "We look forward to seeing you soon!"
        ),
    )


def register_email_event_handlers(event_bus, email_service: EmailServiceInterface):
    # Async handlers via Celery for pub/sub style event processing.
    event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")
    event_bus.subscribe_task(
        ReservationCreated,
        "shared.tasks.send_reservation_confirmation_email",
    )
    event_bus.subscribe_task(UserRegistered, "shared.tasks.publish_realtime_event")
    event_bus.subscribe_task(ReservationCreated, "shared.tasks.publish_realtime_event")