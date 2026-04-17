import os
from pathlib import Path

from flask import Flask, Response, render_template, flash, redirect, url_for, request, jsonify, stream_with_context
from flask_login import current_user, login_required, logout_user
from flask_wtf.csrf import CSRFError
from dotenv import load_dotenv
import stripe
from pydantic import ValidationError as PydanticValidationError

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from shared.infrastructure import db, migrate, csrf, mail, login_manager, celery, init_celery, EventBus, init_db
from shared.infrastructure import init_booking_draft_store
from shared.infrastructure.email.reservation_payment_publisher import publish_reservation_payment_completed
from shared.infrastructure.message_bus.realtime import stream_realtime_events
from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.application.event_handlers.email_event_handler import register_email_event_handlers

from features.games.presentation.api import games_routes, game_copy_routes
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.presentation.api.payment_routes import (
    configure_payment_routes,
    payment_bp,
)
from features.payments.presentation.api.payment_routes import configure_payment_provider
from features.payments.infrastructure.vipps import VippsAdapter, vipps_callbacks
from features.payments.infrastructure.stripe.stripe_adapter import StripeAdapter
from features.payments.infrastructure.stripe.stripe_webhook import bp as stripe_webhook_bp
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.reservations.presentation.api import reservation_routes
from features.tables.presentation.api import table_routes
from features.users.presentation.api import auth_routes, steward_routes
from features.users.application.use_cases.user_use_cases import UpdateOwnProfileCommand
from features.users.presentation.api.deps import get_update_profile_use_case
from features.users.presentation.schemas.user_schema import UserUpdate
from features.users.infrastructure import UserDB as User
from shared.domain.exceptions import ValidationError as DomainValidationError


def create_app(config_name: str = None):
    """
    Application factory function.
    
    Args:
        config_name: 'development', 'testing', or 'production'
                    Defaults to FLASK_ENV environment variable
    """
    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "templates")
    )
    static_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "static")
    )
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Ensure environment variables are loaded even when running from workspace root.
    env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_file, override=False)

    # Configuration
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    app.config.from_object(f"config.{config_name.capitalize()}Config")

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    init_booking_draft_store(app)
    login_manager.login_view = "login_page"
    login_manager.login_message = "Please sign in to continue."

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return {"error": "Authentication required"}, 401
        return redirect(url_for("login_page", next=request.path))

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    celery_app = init_celery(app)
    app.celery_app = celery_app

    # Initialize event bus and email service
    event_bus = EventBus()
    email_service = FlaskMailService(mail)
    register_email_event_handlers(event_bus, email_service)
    app.event_bus = event_bus

    # Register blueprints
    register_blueprints(app)
    app.register_blueprint(stripe_webhook_bp)

    # Register error handlers
    register_error_handlers(app)

    if os.getenv("FLASK_ENV") == "development":
        from features.payments.infrastructure.vipps.mock_vipps import mock_vipps
        app.register_blueprint(mock_vipps)
        # development-only mock vipps blueprint registered above

    
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
        if session_id and app.config.get("STRIPE_SECRET_KEY"):
            try:
                stripe.api_key = app.config["STRIPE_SECRET_KEY"]
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                payment_status = getattr(checkout_session, "payment_status", None)
                if payment_status is None and isinstance(checkout_session, dict):
                    payment_status = checkout_session.get("payment_status")
                is_paid = payment_status == "paid"
            except Exception:
                app.logger.exception("Could not verify Stripe checkout session: %s", session_id)

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

    @app.route("/", methods=["GET"])
    def home():
        return render_template("index.html")

    @app.route("/games", methods=["GET"])
    def games_page():
        return render_template("games.html")

    @app.route("/booking", methods=["GET"])
    @login_required
    def booking_page():
        return render_template("booking.html")

    @app.route("/my-bookings", methods=["GET"])
    @login_required
    def my_bookings_page():
        return render_template("my_bookings.html")

    @app.route("/reservations/confirmation/<int:reservation_id>", methods=["GET"])
    @login_required
    def reservation_confirmation_page(reservation_id: int):
        return render_template("booking_confirmation.html", reservation_id=reservation_id)

    @app.route("/login", methods=["GET"])
    def login_page():
        return render_template("login.html")

    @app.route("/register", methods=["GET"])
    def register_page():
        return render_template("register.html")

    @app.route('/me', methods=['GET', 'POST'])
    @login_required
    def me():
        if request.method == "POST":
            try:
                payload = UserUpdate.model_validate(request.form.to_dict())
            except PydanticValidationError:
                flash("Profile update failed. Please check your input.", "error")
                return redirect(url_for("me"))

            use_case = get_update_profile_use_case()
            try:
                use_case.execute(
                    UpdateOwnProfileCommand(
                        user_id=current_user.id,
                        name=payload.name,
                        phone=payload.phone,
                    ),
                    current_user,
                )
            except DomainValidationError as exc:
                flash(str(exc), "error")
                return redirect(url_for("me"))

            flash("Profile updated successfully.", "success")
            return redirect(url_for("me"))

        return render_template("account.html", user=current_user)


    @app.route('/steward', methods=['GET'])
    @login_required
    def steward_page():
        # Only staff or admin users can access the steward dashboard
        if getattr(current_user, "role", None) not in ("staff", "admin"):
            flash("Staff access required.", "error")
            return redirect(url_for("home"))

        return render_template("steward_dashboard.html")


    @app.route('/steward/pending', methods=['GET'])
    @login_required
    def steward_pending_page():
        if getattr(current_user, "role", None) not in ("staff", "admin"):
            flash("Staff access required.", "error")
            return redirect(url_for("home"))
        return render_template("steward_pending.html")


    @app.route('/steward/seated', methods=['GET'])
    @login_required
    def steward_seated_page():
        if getattr(current_user, "role", None) not in ("staff", "admin"):
            flash("Staff access required.", "error")
            return redirect(url_for("home"))
        return render_template("steward_seated.html")


    @app.route('/steward/game-copies', methods=['GET'])
    @login_required
    def steward_game_copies_page():
        if getattr(current_user, "role", None) not in ("staff", "admin"):
            flash("Staff access required.", "error")
            return redirect(url_for("home"))
        return render_template("steward_game_copies.html")


    @app.route('/steward/incidents', methods=['GET'])
    @login_required
    def steward_incidents_page():
        if getattr(current_user, "role", None) not in ("staff", "admin"):
            flash("Staff access required.", "error")
            return redirect(url_for("home"))
        return render_template("steward_incidents.html")


    @app.route('/steward/incidents/create', methods=['GET'])
    @login_required
    def steward_create_incident_page():
        if getattr(current_user, "role", None) not in ("staff", "admin"):
            flash("Staff access required.", "error")
            return redirect(url_for("home"))
        return render_template("create_incident.html")

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "success")
        return redirect(url_for("home"))

    @app.route("/api/events/stream", methods=["GET"])
    @login_required
    def realtime_event_stream():
        try:
            response = Response(
                stream_with_context(stream_realtime_events()),
                mimetype="text/event-stream",
            )
        except RuntimeError as exc:
            return {"error": str(exc)}, 503
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    # Create database tables
    with app.app_context():
        init_db(app)

        # Note: demo data seeding is handled by the standalone script `scripts/seed_demo_data.py`.

    return app


def register_blueprints(app: Flask):
    """Register all API blueprints."""
    repo = PaymentRepository()
    configure_payment_routes(repo)
    vipps = VippsAdapter()
    stripe_key = (app.config.get("STRIPE_SECRET_KEY") or "").strip()
    if stripe_key:
        configure_payment_provider(StripeAdapter(stripe_key, app.config["APP_BASE_URL"]))
    else:
        app.logger.warning("STRIPE_SECRET_KEY is missing; using VippsAdapter as payment provider fallback")
        configure_payment_provider(vipps)
    app.register_blueprint(vipps_callbacks)

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(games_routes.bp)
    app.register_blueprint(game_copy_routes.bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(reservation_routes.bp)
    app.register_blueprint(table_routes.bp)
    app.register_blueprint(steward_routes.bp)


def register_error_handlers(app: Flask):
    """Register global error handlers."""

    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error"}, 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.path.startswith("/api/"):
            return {"error": error.description or "CSRF validation failed"}, 400
        return {"error": error.description or "CSRF validation failed"}, 400
