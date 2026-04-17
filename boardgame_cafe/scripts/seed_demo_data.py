import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import create_app
from features.bookings.application.use_cases.booking_lifecycle_use_cases import BookingCommand
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.game_tag_db import GameTagDB
from features.games.infrastructure.database.game_tag_link_db import GameTagLinkDB
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.reservations.presentation.api.deps import get_create_booking_handler
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

from seed_games import seed_games


DEMO_USERS = [
    {
        "role": "customer",
        "name": "a",
        "email": "a@a.a",
        "phone": None,
        "password": "aaaaaaaa",
    },
    {
        "role": "customer",
        "name": "b",
        "email": "b@b.b",
        "phone": None,
        "password": "bbbbbbbb",
    },
    {
        "role": "staff",
        "name": "steward",
        "email": "steward@example.com",
        "phone": None,
        "password": "Stewardpw",
    },
    {
        "role": "admin",
        "name": "admin",
        "email": "admin@example.com",
        "phone": None,
        "password": "Adminpw123",
    },
]


DEMO_GAME_TAGS = {
    "strategy": ["Ticket to Ride", "Catan", "7 Wonders", "Risk", "Chess"],
    "family": ["Yatzy", "Monopoly", "UNO", "Scrabble", "Trivial Pursuit"],
    "party": ["Secret Hitler", "UNO", "Ligretto"],
    "quick-play": ["Yatzy", "Ligretto", "UNO", "Othello"],
}


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


def ensure_booking_link_columns() -> None:
    """Add booking-oriented link columns for legacy local databases."""
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name

    if inspector.has_table("table_reservations"):
        table_columns = {
            col["name"] for col in inspector.get_columns("table_reservations")
        }
        if "booking_id" not in table_columns:
            if dialect == "sqlite":
                db.session.execute(
                    text("ALTER TABLE table_reservations ADD COLUMN booking_id INTEGER")
                )
            elif dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE table_reservations "
                        "ADD COLUMN IF NOT EXISTS booking_id INTEGER"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE table_reservations ADD COLUMN booking_id INTEGER")
                )

            if "reservation_id" in table_columns:
                db.session.execute(
                    text(
                        "UPDATE table_reservations "
                        "SET booking_id = reservation_id "
                        "WHERE booking_id IS NULL"
                    )
                )

    if inspector.has_table("game_reservations"):
        game_columns = {col["name"] for col in inspector.get_columns("game_reservations")}

        if "booking_id" not in game_columns:
            if dialect == "sqlite":
                db.session.execute(
                    text("ALTER TABLE game_reservations ADD COLUMN booking_id INTEGER")
                )
            elif dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE game_reservations "
                        "ADD COLUMN IF NOT EXISTS booking_id INTEGER"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE game_reservations ADD COLUMN booking_id INTEGER")
                )

            if "reservation_id" in game_columns:
                db.session.execute(
                    text(
                        "UPDATE game_reservations "
                        "SET booking_id = reservation_id "
                        "WHERE booking_id IS NULL"
                    )
                )

        if "requested_game_id" not in game_columns:
            if dialect == "sqlite":
                db.session.execute(
                    text(
                        "ALTER TABLE game_reservations ADD COLUMN requested_game_id INTEGER"
                    )
                )
            elif dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE game_reservations "
                        "ADD COLUMN IF NOT EXISTS requested_game_id INTEGER"
                    )
                )
            else:
                db.session.execute(
                    text(
                        "ALTER TABLE game_reservations ADD COLUMN requested_game_id INTEGER"
                    )
                )

            if "game_id" in game_columns:
                db.session.execute(
                    text(
                        "UPDATE game_reservations "
                        "SET requested_game_id = game_id "
                        "WHERE requested_game_id IS NULL"
                    )
                )

        if "game_copy_id" not in game_columns and "copy_id" in game_columns:
            if dialect == "sqlite":
                db.session.execute(
                    text("ALTER TABLE game_reservations ADD COLUMN game_copy_id INTEGER")
                )
            elif dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE game_reservations "
                        "ADD COLUMN IF NOT EXISTS game_copy_id INTEGER"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE game_reservations ADD COLUMN game_copy_id INTEGER")
                )

            db.session.execute(
                text(
                    "UPDATE game_reservations "
                    "SET game_copy_id = copy_id "
                    "WHERE game_copy_id IS NULL"
                )
            )

    db.session.commit()


def clear_database() -> None:
    """Remove all rows so the seed starts from an empty database."""
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
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


def seed_game_tags() -> tuple[int, int, int]:
    inserted_tags = 0
    inserted_links = 0

    existing_tags = {
        tag.name: tag
        for tag in GameTagDB.query.order_by(GameTagDB.id.asc()).all()
    }

    for tag_name in DEMO_GAME_TAGS:
        normalized = tag_name.strip().lower()
        tag = existing_tags.get(normalized)
        if tag is None:
            tag = GameTagDB(name=normalized)
            db.session.add(tag)
            db.session.flush()
            existing_tags[normalized] = tag
            inserted_tags += 1

    games_by_title = {game.title: game for game in GameDB.query.order_by(GameDB.id.asc()).all()}
    existing_links = {
        (link.game_id, link.game_tag_id)
        for link in GameTagLinkDB.query.order_by(GameTagLinkDB.id.asc()).all()
    }

    for tag_name, game_titles in DEMO_GAME_TAGS.items():
        tag = existing_tags.get(tag_name)
        if tag is None:
            continue

        for game_title in game_titles:
            game = games_by_title.get(game_title)
            if game is None:
                continue

            link_key = (game.id, tag.id)
            if link_key in existing_links:
                continue

            db.session.add(GameTagLinkDB(game_id=game.id, game_tag_id=tag.id))
            existing_links.add(link_key)
            inserted_links += 1

    return inserted_tags, 0, inserted_links


def seed_users() -> tuple[int, int]:
    inserted = 0
    updated = 0

    existing = {user.email: user for user in UserDB.query.all()}

    for user_data in DEMO_USERS:
        row = existing.get(user_data["email"])
        target_password_hash = generate_password_hash(user_data["password"])

        if row is None:
            db.session.add(
                UserDB(
                    role=user_data["role"],
                    name=user_data["name"],
                    email=user_data["email"],
                    phone=user_data["phone"],
                    password_hash=target_password_hash,
                    force_password_change=False,
                )
            )
            inserted += 1
            continue

        changed = False
        for field in ("role", "name", "phone"):
            if getattr(row, field) != user_data[field]:
                setattr(row, field, user_data[field])
                changed = True

        if not check_password_hash(row.password_hash, user_data["password"]):
            row.password_hash = target_password_hash
            changed = True
        if row.force_password_change:
            row.force_password_change = False
            changed = True

        if changed:
            updated += 1

    return inserted, updated


def _booking_seed_rows(base_day: datetime) -> list[dict]:
    return [
        {
            "email": "a@a.a",
            "table_nr": "T2",
            "start_ts": base_day.replace(hour=17, minute=0, second=0, microsecond=0),
            "end_ts": base_day.replace(hour=19, minute=0, second=0, microsecond=0),
            "party_size": 4,
            "notes": "Demo booking with two game requests",
            "game_slots": [0, 1],
        },
        {
            "email": "b@b.b",
            "table_nr": "T4",
            "start_ts": base_day.replace(hour=19, minute=30, second=0, microsecond=0),
            "end_ts": base_day.replace(hour=21, minute=30, second=0, microsecond=0),
            "party_size": 5,
            "notes": "Demo booking with one game request",
            "game_slots": [2],
        },
        {
            "email": "a@a.a",
            "table_nr": "T1",
            "start_ts": (base_day + timedelta(days=1)).replace(
                hour=15, minute=0, second=0, microsecond=0
            ),
            "end_ts": (base_day + timedelta(days=1)).replace(
                hour=17, minute=0, second=0, microsecond=0
            ),
            "party_size": 2,
            "notes": "Follow-up booking next day",
            "game_slots": [3],
        },
    ]


def _uses_legacy_table_reservation_shape() -> bool:
    inspector = inspect(db.engine)
    if not inspector.has_table("table_reservations"):
        return False

def seed_bookings() -> tuple[int, int, int]:
    inserted_bookings = 0
    inserted_game_links = 0
    inserted_payments = 0

    users_by_email = {user.email: user for user in UserDB.query.all()}
    tables_by_nr = {table.table_nr: table for table in TableDB.query.all()}
    games = GameDB.query.order_by(GameDB.id.asc()).all()
    if not users_by_email or not tables_by_nr or not games:
        return inserted_bookings, inserted_game_links, inserted_payments

    base_day = datetime.now() + timedelta(days=1)
    seed_rows = _booking_seed_rows(base_day)

    existing_keys = {
        (row.customer_id, row.start_ts, row.end_ts)
        for row in BookingDB.query.order_by(BookingDB.id.asc()).all()
    }

    create_booking = get_create_booking_handler()

    for row in seed_rows:
        customer = users_by_email.get(row["email"])
        table = tables_by_nr.get(row["table_nr"])
        if customer is None or table is None:
            continue

        booking_key = (customer.id, row["start_ts"], row["end_ts"])
        if booking_key in existing_keys:
            continue

        game_requests = [
            {"requested_game_id": games[idx % len(games)].id}
            for idx in row["game_slots"]
        ]

        booking, reservation_games, payment = create_booking(
            BookingCommand(
                customer_id=customer.id,
                table_id=table.id,
                start_ts=row["start_ts"],
                end_ts=row["end_ts"],
                party_size=row["party_size"],
                notes=row["notes"],
            ),
            games=game_requests,
        )
        inserted_bookings += 1
        inserted_game_links += len(reservation_games)
        inserted_payments += 1 if payment is not None else 0

        existing_keys.add(booking_key)

    return inserted_bookings, inserted_game_links, inserted_payments


def _count_demo_records() -> tuple[int, int, int]:
    booking_ids = [
        booking.id
        for booking in BookingDB.query.filter(
            BookingDB.notes.in_(
                [
                    "Demo booking with two game requests",
                    "Demo booking with one game request",
                    "Follow-up booking next day",
                ]
            )
        ).all()
    ]
    if not booking_ids:
        return 0, 0, 0

    table_links = (
        db.session.query(TableReservationDB)
        .filter(TableReservationDB.booking_id.in_(booking_ids))
        .count()
    )
    game_links = (
        db.session.query(GameReservationDB)
        .filter(GameReservationDB.booking_id.in_(booking_ids))
        .count()
    )
    payments = (
        db.session.query(PaymentDB)
        .filter(PaymentDB.booking_id.in_(booking_ids))
        .count()
    )
    return table_links, game_links, payments


def seed_demo_data() -> None:
    app = create_app()

    with app.app_context():
        ensure_floor_column_for_tables()
        ensure_booking_link_columns()
        clear_database()
        g_inserted, g_updated, g_total = seed_games()
        gt_inserted, gt_updated, gtl_inserted = seed_game_tags()
        t_inserted, t_updated = seed_tables()
        c_inserted, c_updated = seed_game_copies()
        u_inserted, u_updated = seed_users()
        b_inserted, bg_inserted, bp_inserted = seed_bookings()

        if any(
            (
                g_inserted,
                g_updated,
                gt_inserted,
                gt_updated,
                gtl_inserted,
                t_inserted,
                t_updated,
                c_inserted,
                c_updated,
                u_inserted,
                u_updated,
                b_inserted,
                bg_inserted,
                bp_inserted,
            )
        ):
            db.session.commit()

        link_count, game_link_count, payment_count = _count_demo_records()

    print(
        "Demo data seeded: "
        f"games inserted={g_inserted}, updated={g_updated}, total={g_total}; "
        f"game-tags inserted={gt_inserted}, updated={gt_updated}, links inserted={gtl_inserted}; "
        f"tables inserted={t_inserted}, updated={t_updated}; "
        f"copies inserted={c_inserted}, updated={c_updated}; "
        f"users inserted={u_inserted}, updated={u_updated}; "
        f"bookings inserted={b_inserted}, game-links inserted={bg_inserted}, payments inserted={bp_inserted}; "
        f"demo table-links total={link_count}, demo game-links total={game_link_count}, demo payments total={payment_count}"
    )


if __name__ == "__main__":
    seed_demo_data()
