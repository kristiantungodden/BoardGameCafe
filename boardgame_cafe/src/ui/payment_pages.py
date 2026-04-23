from flask import Flask, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from features.payments.composition.payment_use_case_factories import (
    get_payment_cancel_handler,
    get_payment_success_handler,
)

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

        # Canonicalize URL to avoid exposing mutable query parameters.
        if request.args:
            return redirect(url_for("payment_success_page", payment_id=payment_id))

        try:
            payment = get_payment_success_handler()(payment_id, current_user)
        except ValueError:
            abort(404)
        except PermissionError:
            abort(403)

        is_paid = str(payment.status) == "paid"

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

        # Canonicalize URL to avoid exposing mutable query parameters.
        if request.args:
            return redirect(url_for("payment_cancel_page", payment_id=payment_id))

        try:
            payment = get_payment_cancel_handler()(payment_id, current_user)
        except ValueError:
            abort(404)
        except PermissionError:
            abort(403)

        return render_template(
            "payment_result.html",
            status="cancelled",
            title="Payment Cancelled",
            message="Payment was cancelled. You can try again from your booking page.",
            booking_id=payment.booking_id,
            payment_id=payment.id,
        )
