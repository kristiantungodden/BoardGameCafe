from flask import Flask, render_template, flash, redirect, url_for
from flask_login import current_user, login_required, logout_user
import os

from shared.infrastructure import db, migrate, csrf, mail, login_manager, celery, init_celery, init_db

from features.games.presentation.api import games_routes
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.presentation.api.payment_routes import (
    configure_payment_routes,
    payment_bp,
)
from features.reservations.presentation.api import reservation_routes
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

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    celery_app = init_celery(app)
    app.celery_app = celery_app

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    @app.route("/", methods=["GET"])
    def home():
        return render_template("index.html")

    @app.route("/games", methods=["GET"])
    def games_page():
        return render_template("games.html")

    @app.route("/reservations", methods=["GET"])
    def reservations_page():
        return render_template("reservations.html")

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
    configure_payment_routes(PaymentRepository())

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(games_routes.bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(reservation_routes.bp)
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
