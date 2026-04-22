from flask import Flask, current_app, render_template, request
from flask_login import login_required
from features.payments.application.services.booking_payment_lifecycle import (
    confirm_booking_after_success,
    fail_payment_and_cleanup_created_booking,
)
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

        stripe_payment_status = None
        is_paid = False
        if session_id and current_app.config.get("STRIPE_SECRET_KEY"):
            try:
                stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                stripe_payment_status = getattr(checkout_session, "payment_status", None)
                if stripe_payment_status is None and isinstance(checkout_session, dict):
                    stripe_payment_status = checkout_session.get("payment_status")
                is_paid = stripe_payment_status == "paid"
            except Exception:
                current_app.logger.exception("Could not verify Stripe checkout session: %s", session_id)

        if payment and is_paid:
            resolved_booking_id, changed = confirm_booking_after_success(
                payment_id=payment.id,
                booking_id=booking_id,
            )
            if changed and resolved_booking_id is not None:
                publish_reservation_payment_completed(resolved_booking_id)

        if stripe_payment_status == "unpaid":
            fail_payment_and_cleanup_created_booking(
                payment_id=payment_id,
                booking_id=booking_id,
                reason="stripe_checkout_unpaid",
            )
            return render_template(
                "payment_result.html",
                status="failed",
                title="Payment Confirmation",
                message="Payment failed. Your provisional booking was removed.",
                booking_id=booking_id,
                payment_id=payment_id,
            )

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

        fail_payment_and_cleanup_created_booking(
            payment_id=payment_id,
            booking_id=booking_id,
            reason="customer_cancelled_checkout",
        )

        return render_template(
            "payment_result.html",
            status="cancelled",
            title="Payment Cancelled",
            message="Payment was cancelled. You can try again from your booking page.",
            booking_id=booking_id,
            payment_id=payment_id,
        )
