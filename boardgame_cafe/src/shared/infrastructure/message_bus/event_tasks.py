from __future__ import annotations

from shared.infrastructure.extensions import mail
from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.infrastructure.message_bus.celery_app import celery
from shared.infrastructure.message_bus.realtime import publish_realtime_event


@celery.task(name="shared.tasks.send_welcome_email")
def send_welcome_email(event_payload: dict) -> None:
    email = event_payload.get("data", {}).get("email")
    if not email:
        return
    FlaskMailService(mail).send_email(
        subject="Welcome to Dicer.no!",
        sender=None,
        recipients=[email],
        body="Thank you for signing up at Dicer.no! \n\nWe are excited to have you as part of our community. Stay tuned for updates on events, new games, and special offers!"
    )


@celery.task(name="shared.tasks.send_reservation_confirmation_email")
def send_reservation_confirmation_email(event_payload: dict) -> None:
    data = event_payload.get("data", {})
    recipient = data.get("user_email")
    table_numbers = data.get("table_numbers", [])
    start_ts = data.get("start_ts", "")
    end_ts = data.get("end_ts", "")
    party_size = data.get("party_size", "")
    if not recipient:
        return
    details = (
        f"table_numbers={table_numbers}, start_ts={start_ts}, "
        f"end_ts={end_ts}, party_size={party_size}"
    )
    FlaskMailService(mail).send_email(
        subject="Your Dicer.no Reservation Confirmation",
        sender=None,
        recipients=[recipient],
        body=f"Thank you for your reservation at Dicer.no! \n\nHere are your reservation details:\n{details}\n\nWe look forward to seeing you soon!"
    )

# HER MÅ VÆRE NOE FOR RESET PASSORD SENERE.


@celery.task(name="shared.tasks.publish_realtime_event")
def publish_realtime_event_task(event_payload: dict) -> None:
    publish_realtime_event(event_payload)
