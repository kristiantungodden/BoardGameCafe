from __future__ import annotations

import logging

from flask import current_app, has_app_context

from shared.infrastructure.extensions import mail
from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.infrastructure.message_bus.celery_app import celery
from shared.infrastructure.message_bus.realtime import publish_realtime_event
from shared.infrastructure.qr_codes import generate_qr_svg, get_or_create_reservation_qr_token

logger = logging.getLogger(__name__)


def _public_base_url() -> str:
    configured = current_app.config.get("PUBLIC_BASE_URL") or current_app.config.get("APP_BASE_URL")
    if configured:
        return str(configured).rstrip("/")

    server_name = current_app.config.get("SERVER_NAME")
    scheme = current_app.config.get("PREFERRED_URL_SCHEME", "http")
    if server_name:
        return f"{scheme}://{server_name}".rstrip("/")

    return "http://127.0.0.1:5000"


@celery.task(
    name="shared.tasks.send_welcome_email",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
)
def send_welcome_email(self, event_payload: dict) -> None:
    email = event_payload.get("data", {}).get("email")
    if not email:
        return
    logger.info("Sending welcome email to %s (attempt %d)", email, self.request.retries + 1)
    try:
        FlaskMailService(mail).send_email(
            subject="Welcome to Dicer.no!",
            sender=None,
            recipients=[email],
            body="Thank you for signing up at Dicer.no! \n\nWe are excited to have you as part of our community. Stay tuned for updates on events, new games, and special offers!"
        )
        logger.info("Welcome email sent to %s", email)
    except Exception as exc:
        logger.error("Failed to send welcome email to %s: %s", email, exc)
        raise


@celery.task(
    name="shared.tasks.send_reservation_confirmation_email",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
)
def send_reservation_confirmation_email(self, event_payload: dict) -> None:
    data = event_payload.get("data", {})
    recipient = data.get("user_email")
    reservation_id = data.get("reservation_id")
    user_id = data.get("user_id")
    table_numbers = data.get("table_numbers", [])
    start_ts = data.get("start_ts", "")
    end_ts = data.get("end_ts", "")
    party_size = data.get("party_size", "")
    if not recipient:
        return

    logger.info("Sending reservation confirmation email to %s (attempt %d)", recipient, self.request.retries + 1)
    qr_lines = ""
    attachments = []

    if reservation_id and user_id and has_app_context():
        secret_key = current_app.config.get("SECRET_KEY")
        if secret_key:
            token = get_or_create_reservation_qr_token(
                secret_key,
                user_id=int(user_id),
                reservation_id=int(reservation_id),
            )
            checkin_path = f"/api/reservations/checkin/{token}"
            checkin_url = f"{_public_base_url()}{checkin_path}"
            qr_svg = generate_qr_svg(checkin_url)
            attachments.append(
                (
                    f"reservation-{reservation_id}-checkin-qr.svg",
                    "image/svg+xml",
                    qr_svg.encode("utf-8"),
                )
            )
            qr_lines = (
                "\n\nCheck-in QR included as attachment: "
                f"reservation-{reservation_id}-checkin-qr.svg"
                f"\nStaff check-in URL (fallback): {checkin_url}"
            )

    details = (
        f"table_numbers={table_numbers}, start_ts={start_ts}, "
        f"end_ts={end_ts}, party_size={party_size}"
    )
    send_kwargs = {
        "subject": "Your Dicer.no Reservation Confirmation",
        "sender": None,
        "recipients": [recipient],
        "body": (
            "Thank you for your reservation at Dicer.no! "
            f"\n\nHere are your reservation details:\n{details}"
            f"{qr_lines}"
            "\n\nWe look forward to seeing you soon!"
        ),
    }
    if attachments:
        send_kwargs["attachments"] = attachments
    try:
        FlaskMailService(mail).send_email(**send_kwargs)
        logger.info("Reservation confirmation email sent to %s", recipient)
    except Exception as exc:
        logger.error("Failed to send reservation confirmation email to %s: %s", recipient, exc)
        raise

# HER MÅ VÆRE NOE FOR RESET PASSORD SENERE.


@celery.task(name="shared.tasks.publish_realtime_event")
def publish_realtime_event_task(event_payload: dict) -> None:
    publish_realtime_event(event_payload)
