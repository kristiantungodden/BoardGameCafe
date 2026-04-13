from flask import Flask, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required, logout_user
from flask_wtf.csrf import CSRFError
import os

from shared.infrastructure import db, migrate, csrf, mail, login_manager, celery, init_celery, EventBus, init_db
from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.application.event_handlers.email_event_handler import register_email_event_handlers

from features.games.presentation.api import games_routes
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.presentation.api.payment_routes import (
    configure_payment_routes,
    payment_bp,
)
from features.payments.presentation.api.payment_routes import configure_payment_provider
from features.payments.infrastructure.vipps import VippsAdapter, vipps_callbacks
from features.reservations.presentation.api import reservation_routes
from features.tables.presentation.api import table_routes
from features.users.presentation.api import auth_routes, steward_routes
from features.users.infrastructure import UserDB as User

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

    # Register error handlers
    register_error_handlers(app)

    if os.getenv("FLASK_ENV") == "development":
        from features.payments.infrastructure.vipps.mock_vipps import mock_vipps
        app.register_blueprint(mock_vipps)

    
    @app.route("/payments/<int:booking_id>")
    @login_required
    def payment_page(booking_id):
        return render_template("payment.html", booking_id=booking_id)

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

    @app.route("/my-page", methods=["GET"])
    @login_required
    def my_page():
        return render_template("my_page.html")

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

    @app.route('/me', methods=['GET'])
    @login_required
    def me():
        return render_template("account.html", user=current_user)

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "success")
        return redirect(url_for("home"))

    # Create database tables
    with app.app_context():
        init_db(app)

    return app


def register_blueprints(app: Flask):
    """Register all API blueprints."""
    repo = PaymentRepository()
    configure_payment_routes(repo)
    # instantiate Vipps adapter (reads env vars if present)
    vipps = VippsAdapter()
    configure_payment_provider(vipps)
    app.register_blueprint(vipps_callbacks)

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(games_routes.bp)
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
