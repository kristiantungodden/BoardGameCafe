from shared.infrastructure.extensions import db
from shared.infrastructure.database.model_registry import register_all_models

def init_db(app=None):
    """Initialize database tables. Call with Flask app context."""
    # Register ORM models lazily at startup to avoid circular imports during module loading.
    register_all_models()

    if app is not None:
        with app.app_context():
            db.create_all()
    else:
        db.create_all()
