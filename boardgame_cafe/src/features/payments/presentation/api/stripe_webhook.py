import stripe
from flask import Blueprint, request, current_app
from features.payments.application.services.booking_payment_lifecycle import (
    confirm_booking_after_success,
    fail_payment_and_cleanup_created_booking,
)
from features.payments.composition.payment_use_case_factories import (
    _booking_repo,
    _game_reservation_repo,
    _payment_repo,
    _reservation_qr_repo,
    _status_history_repo,
    _table_reservation_repo,
)
from shared.infrastructure import csrf
from shared.infrastructure.email.reservation_payment_publisher import publish_reservation_payment_completed

bp = Blueprint("stripe_webhook", __name__, url_prefix="/payments/stripe")


@bp.post("/webhook")
@csrf.exempt
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception:
        return {"error": "Invalid webhook"}, 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment_id = session.get("metadata", {}).get("payment_id")

        resolved_booking_id, changed = confirm_booking_after_success(
            payment_repo=_payment_repo,
            booking_repo=_booking_repo,
            status_history_repo=_status_history_repo,
            payment_id=int(payment_id) if payment_id else None,
        )
        if changed and resolved_booking_id is not None:
            publish_reservation_payment_completed(resolved_booking_id)

    if event["type"] in {"checkout.session.expired", "checkout.session.async_payment_failed"}:
        session = event["data"]["object"]
        payment_id = session.get("metadata", {}).get("payment_id")
        fail_payment_and_cleanup_created_booking(
            payment_repo=_payment_repo,
            booking_repo=_booking_repo,
            status_history_repo=_status_history_repo,
            table_reservation_repo=_table_reservation_repo,
            game_reservation_repo=_game_reservation_repo,
            reservation_qr_repo=_reservation_qr_repo,
            payment_id=int(payment_id) if payment_id else None,
        )

    return {"status": "ok"}
