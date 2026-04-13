from shared.infrastructure.extensions import db
from shared.infrastructure.database.model_registry import register_all_models
from sqlalchemy import inspect, text

def init_db(app=None):
    """Initialize database tables. Call with Flask app context."""
    # Register ORM models lazily at startup to avoid circular imports during module loading.
    register_all_models()

    if app is not None:
        with app.app_context():
            db.create_all()
            _ensure_booking_status_history_actor_columns()
    else:
        db.create_all()
        _ensure_booking_status_history_actor_columns()


def _ensure_booking_status_history_actor_columns() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "booking_status_history" not in table_names:
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("booking_status_history")
    }
    statements: list[str] = []

    if "actor_user_id" not in existing_columns:
        statements.append(
            "ALTER TABLE booking_status_history ADD COLUMN actor_user_id INTEGER"
        )

    if "actor_role" not in existing_columns:
        statements.append(
            "ALTER TABLE booking_status_history ADD COLUMN actor_role VARCHAR(30)"
        )

    if not statements:
        return

    with db.engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
