from infrastructure.extensions import db


def init_db(app=None):
    """Initialize database tables. Call with Flask app context."""
    if app is not None:
        with app.app_context():
            db.create_all()
    else:
        db.create_all()
