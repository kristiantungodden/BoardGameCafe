from shared.infrastructure.extensions import db
from shared.infrastructure.database.model_registry import register_all_models

# Register all ORM model classes before any queries or create_all() calls.
# This ensures string-based relationships (e.g., relationship("TableDB")) resolve correctly.
register_all_models()

def init_db(app=None):
    """Initialize database tables. Call with Flask app context."""
    if app is not None:
        with app.app_context():
            db.create_all()
    else:
        db.create_all()
