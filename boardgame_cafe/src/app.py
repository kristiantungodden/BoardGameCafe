import os
from pathlib import Path

from flask import Flask, Response, request, jsonify, stream_with_context, redirect, url_for
from flask_login import login_required
from flask_wtf.csrf import CSRFError
from dotenv import load_dotenv
import stripe

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from shared.infrastructure import db, migrate, csrf, mail, login_manager, celery, init_celery, EventBus, init_db
from shared.infrastructure import init_booking_draft_store
from shared.infrastructure.message_bus.realtime import stream_realtime_events
from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.application.event_handlers.email_event_handler import register_email_event_handlers
from shared.application.event_handlers.realtime_event_handler import (
    register_realtime_event_handlers,
)

from features.games.presentation.api import games_routes, game_copy_routes, game_rating_routes
from features.bookings.infrastructure.repositories.booking_repository import SqlAlchemyBookingRepository
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.presentation.api.payment_routes import (
    configure_payment_routes,
    payment_bp,
)
from features.payments.presentation.api.payment_routes import configure_payment_provider
from features.payments.infrastructure.vipps import VippsAdapter, vipps_callbacks
from features.payments.infrastructure.stripe.stripe_adapter import StripeAdapter
from features.payments.infrastructure.stripe.stripe_webhook import bp as stripe_webhook_bp
from features.reservations.presentation.api import reservation_routes
from features.tables.presentation.api import table_routes
try:
    from features.tables.presentation.api import admin_routes as table_admin_routes
except (ImportError, ModuleNotFoundError):
    table_admin_routes = None
from features.users.presentation.api import auth_routes, admin_routes, steward_routes
from features.users.infrastructure import UserDB as User
from ui import register_ui_pages
from shared.presentation.api.events_routes import bp as events_bp


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
        if request.path.startswith("/admin"):
            return redirect(url_for("admin_login_page", next=request.path))
        return redirect(url_for("login_page", next=request.path))

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def enforce_forced_password_change():
        from flask_login import current_user

        if not getattr(current_user, "is_authenticated", False):
            return None
        if not bool(getattr(current_user, "force_password_change", False)):
            return None

        endpoint = request.endpoint or ""
        if endpoint.startswith("static"):
            return None

        allowed_endpoints = {
            "auth.change_password",
            "auth.logout",
            "password_change_page",
        }
        if endpoint in allowed_endpoints:
            return None

        if request.path.startswith("/api/"):
            return {"error": "Password change required", "requires_password_change": True}, 403

        return redirect(url_for("password_change_page"))

    celery_app = init_celery(app)
    app.celery_app = celery_app

    # Initialize event bus and email service
    event_bus = EventBus()
    email_service = FlaskMailService(mail)
    register_email_event_handlers(event_bus, email_service)
    register_realtime_event_handlers(event_bus)
    app.event_bus = event_bus

    # Register blueprints
    register_blueprints(app)
    register_ui_pages(app)
    app.register_blueprint(stripe_webhook_bp)

    # Register error handlers
    register_error_handlers(app)

    if os.getenv("FLASK_ENV") == "development":
        from features.payments.infrastructure.vipps.mock_vipps import mock_vipps
        app.register_blueprint(mock_vipps)
        # development-only mock vipps blueprint registered above

    
    # `/api/events/stream` is provided by the presentation blueprint
    # `shared.presentation.api.events_routes` to keep presentation
    # concerns separate from application setup.

    # Create database tables
    with app.app_context():
        init_db(app)

        # Note: demo data seeding is handled by the standalone script `scripts/seed_demo_data.py`.

    return app


def register_blueprints(app: Flask):
    """Register all API blueprints."""
    repo = PaymentRepository()
    booking_repo = SqlAlchemyBookingRepository()
    from features.payments.presentation.api.payment_routes import configure_booking_repository

    configure_booking_repository(booking_repo)
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
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(games_routes.bp)
    app.register_blueprint(game_copy_routes.bp)
    app.register_blueprint(game_rating_routes.bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(reservation_routes.bp)
    app.register_blueprint(table_routes.bp)
    if table_admin_routes is not None:
        app.register_blueprint(table_admin_routes.bp)
    app.register_blueprint(steward_routes.bp)
    app.register_blueprint(events_bp)


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
