import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import create_app
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.tables.infrastructure.database.table_db import TableDB
from shared.infrastructure import db
from sqlalchemy import inspect, text


def ensure_floor_column_for_tables() -> None:
    """Add `floor` column for legacy databases before ORM table queries."""
    inspector = inspect(db.engine)
    if not inspector.has_table("cafe_tables"):
        return

    existing_columns = {col["name"] for col in inspector.get_columns("cafe_tables")}
    if "floor" in existing_columns:
        return

    dialect = db.engine.dialect.name
    if dialect == "sqlite":
        db.session.execute(
            text("ALTER TABLE cafe_tables ADD COLUMN floor INTEGER NOT NULL DEFAULT 1")
        )
    elif dialect == "postgresql":
        db.session.execute(
            text(
                "ALTER TABLE cafe_tables "
                "ADD COLUMN IF NOT EXISTS floor INTEGER NOT NULL DEFAULT 1"
            )
        )
    else:
        db.session.execute(text("ALTER TABLE cafe_tables ADD COLUMN floor INTEGER"))
        db.session.execute(text("UPDATE cafe_tables SET floor = 1 WHERE floor IS NULL"))

    db.session.commit()


def seed_tables() -> tuple[int, int]:
    inserted = 0
    updated = 0

    table_seed = [
        {"table_nr": "T1", "capacity": 2, "floor": 1, "zone": "main", "status": "available"},
        {"table_nr": "T2", "capacity": 4, "floor": 1, "zone": "main", "status": "available"},
        {"table_nr": "T3", "capacity": 4, "floor": 1, "zone": "window", "status": "available"},
        {"table_nr": "T4", "capacity": 6, "floor": 2, "zone": "corner", "status": "available"},
        {"table_nr": "T5", "capacity": 8, "floor": 2, "zone": "main", "status": "available"},
    ]

    existing = {t.table_nr: t for t in TableDB.query.all()}

    for table_data in table_seed:
        row = existing.get(table_data["table_nr"])
        if row is None:
            db.session.add(TableDB(**table_data))
            inserted += 1
            continue

        changed = False
        for field in ("capacity", "zone", "status"):
            if getattr(row, field) != table_data[field]:
                setattr(row, field, table_data[field])
                changed = True
        if getattr(row, "floor", None) != table_data["floor"]:
            row.floor = table_data["floor"]
            changed = True
        if changed:
            updated += 1

    return inserted, updated


def seed_game_copies() -> tuple[int, int]:
    inserted = 0
    updated = 0

    games = GameDB.query.order_by(GameDB.id.asc()).all()
    if not games:
        return inserted, updated

    existing = {copy.copy_code: copy for copy in GameCopyDB.query.all()}

    for game in games:
        for copy_idx in (1, 2):
            copy_code = f"G{game.id}-C{copy_idx}"
            row = existing.get(copy_code)
            target = {
                "game_id": game.id,
                "copy_code": copy_code,
                "status": "available",
                "location": "shelf-a",
            }

            if row is None:
                db.session.add(GameCopyDB(**target))
                inserted += 1
                continue

            changed = False
            for field in ("game_id", "status", "location"):
                if getattr(row, field) != target[field]:
                    setattr(row, field, target[field])
                    changed = True
            if changed:
                updated += 1

    return inserted, updated


def seed_demo_data() -> None:
    app = create_app()

    with app.app_context():
        ensure_floor_column_for_tables()
        t_inserted, t_updated = seed_tables()
        c_inserted, c_updated = seed_game_copies()
        if any((t_inserted, t_updated, c_inserted, c_updated)):
            db.session.commit()

    print(
        "Demo data seeded: "
        f"tables inserted={t_inserted}, updated={t_updated}; "
        f"copies inserted={c_inserted}, updated={c_updated}"
    )


if __name__ == "__main__":
    seed_demo_data()
