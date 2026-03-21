from flask import Flask
import os

from infrastructure import db, migrate, csrf, mail, login_manager, celery, init_celery

def create_app(config_name: str = None):
    """
    Application factory function.
    
    Args:
        config_name: 'development', 'testing', or 'production'
                    Defaults to FLASK_ENV environment variable
    """
    app = Flask(__name__)
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
    celery = init_celery(app)
    app.celery_app = celery
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


def register_blueprints(app: Flask):
    """Register all API blueprints."""
    from presentation.api import auth, games, reservations, tables, admin, steward
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(games.bp)
    app.register_blueprint(reservations.bp)
    app.register_blueprint(tables.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(steward.bp)


def register_error_handlers(app: Flask):
    """Register global error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error"}, 500