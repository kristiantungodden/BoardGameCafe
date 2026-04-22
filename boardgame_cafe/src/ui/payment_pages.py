from flask import Flask, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from features.payments.infrastructure.database.payments_db import PaymentDB
from shared.infrastructure import db


def _is_staff_or_admin(user) -> bool:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    return role in {"staff", "admin"} or bool(
        getattr(user, "is_staff", False) or getattr(user, "is_admin", False)
    )


def _can_view_payment_result(payment: PaymentDB) -> bool:
    if _is_staff_or_admin(current_user):
        return True
    booking = getattr(payment, "booking", None)
    if booking is None:
        return False
    return getattr(booking, "customer_id", None) == getattr(current_user, "id", None)


def register_payment_pages(app: Flask) -> None:
    @app.route("/payments/<int:booking_id>")
    @login_required
    def payment_page(booking_id):
        return render_template("payment.html", booking_id=booking_id)

    @app.route("/payments/success", methods=["GET"])
    @app.route("/payments/success/<int:payment_id>", methods=["GET"])
    @login_required
    def payment_success_page(payment_id: int | None = None):
        if payment_id is None:
            payment_id = request.args.get("payment_id", type=int)
        if payment_id is None:
            abort(400)

        payment = db.session.get(PaymentDB, payment_id)
        if payment is None:
            abort(404)
        if not _can_view_payment_result(payment):
            abort(403)

        # Canonicalize URL to avoid exposing mutable query parameters.
        if request.args:
            return redirect(url_for("payment_success_page", payment_id=payment.id))

        is_paid = payment.status == "paid"

        return render_template(
            "payment_result.html",
            status="success" if is_paid else "pending",
            title="Payment Confirmation",
            message=(
                "Payment completed successfully."
                if is_paid
                else "Payment is being verified. Please check your bookings in a moment."
            ),
            booking_id=payment.booking_id,
            payment_id=payment.id,
        )

    @app.route("/payments/cancel", methods=["GET"])
    @app.route("/payments/cancel/<int:payment_id>", methods=["GET"])
    @login_required
    def payment_cancel_page(payment_id: int | None = None):
        if payment_id is None:
            payment_id = request.args.get("payment_id", type=int)
        if payment_id is None:
            abort(400)

        payment = db.session.get(PaymentDB, payment_id)
        if payment is None:
            abort(404)
        if not _can_view_payment_result(payment):
            abort(403)

        if request.args:
            return redirect(url_for("payment_cancel_page", payment_id=payment.id))

        return render_template(
            "payment_result.html",
            status="cancelled",
            title="Payment Cancelled",
            message="Payment was cancelled. You can try again from your booking page.",
            booking_id=payment.booking_id,
            payment_id=payment.id,
        )
