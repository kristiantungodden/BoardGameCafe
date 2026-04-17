import stripe
from flask import Blueprint, request, current_app
from shared.infrastructure import db, csrf
from shared.infrastructure.email.reservation_payment_publisher import publish_reservation_payment_completed
from features.payments.infrastructure.database.payments_db import PaymentDB

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
        payment_id = session["metadata"].get("payment_id")

        payment = db.session.get(PaymentDB, payment_id)
        if payment and payment.status != "paid":
            payment.status = "paid"
            db.session.commit()
            publish_reservation_payment_completed(payment.booking_id)

    return {"status": "ok"}