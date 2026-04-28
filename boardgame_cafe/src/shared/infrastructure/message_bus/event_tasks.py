from __future__ import annotations

import html
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


def _build_reservation_html_email(
    *,
    reservation_id: int | None,
    table_numbers: list,
    start_ts: str,
    end_ts: str,
    party_size,
    checkin_url: str | None,
    qr_cid: str | None,
) -> str:
    reservation_label = "-" if reservation_id is None else str(reservation_id)
    table_label = ", ".join(str(table_number) for table_number in table_numbers) or "-"
    start_label = start_ts or "-"
    end_label = end_ts or "-"
    party_label = "-" if party_size in (None, "") else str(party_size)

    qr_block = ""
    if qr_cid:
        qr_block = (
            '<div style="margin:24px 0;text-align:center;">'
            '<img src="{src}" alt="Reservation check-in QR" '
            'style="display:inline-block;max-width:260px;width:100%;height:auto;" />'
            "</div>"
        ).format(src=f"cid:{qr_cid}")

    checkin_block = ""
    if checkin_url:
        escaped_url = html.escape(checkin_url)
        checkin_block = (
            "<p style=\"margin:16px 0 0 0;line-height:1.5;\">"
            "If the QR code does not render, open this check-in link: "
            f'<a href="{escaped_url}">{escaped_url}</a>'
            "</p>"
        )

    return (
        "<html><body style=\"margin:0;padding:0;background:#f7f7f7;font-family:Arial,sans-serif;color:#1f2937;\">"
        "<div style=\"max-width:640px;margin:0 auto;padding:24px;\">"
        "<div style=\"background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;\">"
        "<h2 style=\"margin:0 0 12px 0;font-size:22px;\">Your Reservation Is Confirmed</h2>"
        f"<p style=\"margin:0 0 16px 0;line-height:1.5;\">Reservation #{html.escape(reservation_label)}</p>"
        "<table style=\"width:100%;border-collapse:collapse;margin:0 0 16px 0;\">"
        "<tr><td style=\"padding:8px 0;font-weight:600;\">Table(s)</td>"
        f"<td style=\"padding:8px 0;\">{html.escape(table_label)}</td></tr>"
        "<tr><td style=\"padding:8px 0;font-weight:600;\">Start</td>"
        f"<td style=\"padding:8px 0;\">{html.escape(start_label)}</td></tr>"
        "<tr><td style=\"padding:8px 0;font-weight:600;\">End</td>"
        f"<td style=\"padding:8px 0;\">{html.escape(end_label)}</td></tr>"
        "<tr><td style=\"padding:8px 0;font-weight:600;\">Party Size</td>"
        f"<td style=\"padding:8px 0;\">{html.escape(party_label)}</td></tr>"
        "</table>"
        "<p style=\"margin:0 0 10px 0;line-height:1.5;\">"
        "Show this QR code to staff when you arrive."
        "</p>"
        f"{qr_block}"
        f"{checkin_block}"
        "<p style=\"margin:20px 0 0 0;line-height:1.5;\">We look forward to seeing you soon!</p>"
        "</div></div></body></html>"
    )


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
    checkin_url = None
    inline_attachments = []
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
            qr_payload = qr_svg.encode("utf-8")
            qr_cid = f"reservation-{reservation_id}-checkin-qr"
            inline_attachments.append(
                (
                    f"reservation-{reservation_id}-checkin-qr.svg",
                    "image/svg+xml",
                    qr_payload,
                    qr_cid,
                )
            )
            attachments.append(
                (
                    f"reservation-{reservation_id}-checkin-qr.svg",
                    "image/svg+xml",
                    qr_payload,
                )
            )
            qr_lines = (
                "\n\nCheck-in QR included as attachment: "
                f"reservation-{reservation_id}-checkin-qr.svg"
                f"\nStaff check-in URL (fallback): {checkin_url}"
            )
    qr_cid = inline_attachments[0][3] if inline_attachments else None

    table_str = ", ".join(str(t) for t in table_numbers)
    details = (
        f"{'Reservation #:':<16}{reservation_id}\n"
        f"{'Table(s):':<16}{table_str}\n"
        f"{'Start:':<16}{start_ts}\n"
        f"{'End:':<16}{end_ts}\n"
        f"{'Party size:':<16}{party_size}"
    )
    html_body = _build_reservation_html_email(
        reservation_id=reservation_id,
        table_numbers=table_numbers,
        start_ts=start_ts,
        end_ts=end_ts,
        party_size=party_size,
        checkin_url=checkin_url,
        qr_cid=qr_cid,
    )
    send_kwargs = {
        "subject": "Your Dicer.no Reservation Confirmation",
        "sender": None,
        "recipients": [recipient],
        "body": (
            "Thank you for your reservation at Dicer.no!"
            f"\n\n{details}"
            f"{qr_lines}"
            "\n\nWe look forward to seeing you soon!"
        ),
        "html": html_body,
    }
    if attachments:
        send_kwargs["attachments"] = attachments
    if inline_attachments:
        send_kwargs["inline_attachments"] = inline_attachments
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
