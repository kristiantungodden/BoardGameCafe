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
    FlaskMailService(mail).send_welcome_email(email)


@celery.task(name="shared.tasks.send_reservation_confirmation_email")
def send_reservation_confirmation_email(event_payload: dict) -> None:
    data = event_payload.get("data", {})
    recipient = data.get("user_email")
    details = data.get("reservation_details", "")
    if not recipient:
        return
    FlaskMailService(mail).send_reservation_confirmation_email(recipient, details)


@celery.task(name="shared.tasks.publish_realtime_event")
def publish_realtime_event_task(event_payload: dict) -> None:
    publish_realtime_event(event_payload)
