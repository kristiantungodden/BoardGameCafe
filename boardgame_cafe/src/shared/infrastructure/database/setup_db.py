from shared.infrastructure import db

from features.reservations.infrastructure.database.table_reservations_db import TableReservation
from features.payments.infrastructure.database.payments_db import PaymentDB

def init_db(app=None):
    """Initialize database tables. Call with Flask app context."""
    if app is not None:
        with app.app_context():
            db.create_all()
    else:
        db.create_all()
