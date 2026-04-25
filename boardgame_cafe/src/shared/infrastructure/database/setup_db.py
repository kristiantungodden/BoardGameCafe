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
            _ensure_users_suspension_column()
            _ensure_users_created_at_column()
            _ensure_cafe_tables_layout_columns()
    else:
        db.create_all()
        _ensure_booking_status_history_actor_columns()
        _ensure_users_suspension_column()
        _ensure_users_created_at_column()
        _ensure_cafe_tables_layout_columns()


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


def _ensure_users_suspension_column() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names:
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("users")
    }
    if "is_suspended" in existing_columns:
        return

    with db.engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN is_suspended BOOLEAN NOT NULL DEFAULT 0")
        )


def _ensure_users_created_at_column() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names:
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("users")
    }
    if "created_at" in existing_columns:
        return

    with db.engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN created_at DATETIME")
        )
        connection.execute(
            text("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL")
        )


def _ensure_cafe_tables_layout_columns() -> None:
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "cafe_tables" not in table_names:
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("cafe_tables")
    }
    statements: list[str] = []

    if "width" not in existing_columns:
        statements.append("ALTER TABLE cafe_tables ADD COLUMN width INTEGER")
    if "height" not in existing_columns:
        statements.append("ALTER TABLE cafe_tables ADD COLUMN height INTEGER")
    if "rotation" not in existing_columns:
        statements.append("ALTER TABLE cafe_tables ADD COLUMN rotation INTEGER")

    if not statements:
        return

    with db.engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
