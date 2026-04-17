from flask import Flask, current_app, render_template, request
from flask_login import login_required
from features.payments.infrastructure.database.payments_db import PaymentDB
from shared.infrastructure import db
from shared.infrastructure.email.reservation_payment_publisher import publish_reservation_payment_completed
import stripe



def register_payment_pages(app: Flask) -> None:
    @app.route("/payments/<int:booking_id>")
    @login_required
    def payment_page(booking_id):
        return render_template("payment.html", booking_id=booking_id)

    @app.route("/payments/success", methods=["GET"])
    def payment_success_page():
        payment_id = request.args.get("payment_id", type=int)
        booking_id = request.args.get("booking_id", type=int)
        session_id = request.args.get("session_id", type=str)

        payment = db.session.get(PaymentDB, payment_id) if payment_id else None
        if payment and not booking_id:
            booking_id = payment.booking_id

        is_paid = False
        if session_id and current_app.config.get("STRIPE_SECRET_KEY"):
            try:
                stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                payment_status = getattr(checkout_session, "payment_status", None)
                if payment_status is None and isinstance(checkout_session, dict):
                    payment_status = checkout_session.get("payment_status")
                is_paid = payment_status == "paid"
            except Exception:
                current_app.logger.exception("Could not verify Stripe checkout session: %s", session_id)

        was_paid = bool(payment and payment.status == "paid")
        if payment and is_paid and not was_paid:
            payment.status = "paid"
            db.session.commit()
            publish_reservation_payment_completed(payment.booking_id)

        return render_template(
            "payment_result.html",
            status="success" if (is_paid or (payment and payment.status == "paid")) else "pending",
            title="Payment Confirmation",
            message=(
                "Payment completed successfully."
                if (is_paid or (payment and payment.status == "paid"))
                else "Payment is being verified. Please check your bookings in a moment."
            ),
            booking_id=booking_id,
            payment_id=payment_id,
        )

    @app.route("/payments/cancel", methods=["GET"])
    def payment_cancel_page():
        payment_id = request.args.get("payment_id", type=int)
        booking_id = request.args.get("booking_id", type=int)
        return render_template(
            "payment_result.html",
            status="cancelled",
            title="Payment Cancelled",
            message="Payment was cancelled. You can try again from your booking page.",
            booking_id=booking_id,
            payment_id=payment_id,
        )
