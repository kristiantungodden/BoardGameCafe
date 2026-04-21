import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import create_app
from features.bookings.application.use_cases.booking_lifecycle_use_cases import BookingCommand
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.game_tag_db import GameTagDB
from features.games.infrastructure.database.game_tag_link_db import GameTagLinkDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.reservations.composition.reservation_use_case_factories import get_create_booking_handler
from features.reservations.infrastructure.database.waitlist_db import WaitlistDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.admin_policy_db import AdminPolicyDB
from features.users.infrastructure.database.announcement_db import AnnouncementDB
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

from seed_games import seed_games


DEMO_USERS = [
    # Quick-login dev shortcuts
    {"role": "customer", "name": "a", "email": "a@a.a", "phone": None, "password": "aaaaaaaa"},
    {"role": "customer", "name": "b", "email": "b@b.b", "phone": None, "password": "bbbbbbbb"},
    # Realistic customers
    {"role": "customer", "name": "Emma Hansen", "email": "emma.hansen@example.com", "phone": "+4791234567", "password": "Password1"},
    {"role": "customer", "name": "Lars Olsen", "email": "lars.olsen@example.com", "phone": "+4798765432", "password": "Password1"},
    {"role": "customer", "name": "Sofie Berg", "email": "sofie.berg@example.com", "phone": None, "password": "Password1"},
    {"role": "customer", "name": "Jonas Vik", "email": "jonas.vik@example.com", "phone": "+4792345678", "password": "Password1"},
    # Staff
    {"role": "staff", "name": "steward", "email": "steward@example.com", "phone": None, "password": "Stewardpw"},
    {"role": "staff", "name": "Maria Lund", "email": "maria.lund@example.com", "phone": "+4745678901", "password": "Stewardpw"},
    # Admin
    {"role": "admin", "name": "admin", "email": "admin@example.com", "phone": None, "password": "Adminpw123"},
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


def ensure_pricing_schema() -> None:
    """Add pricing columns/settings table for legacy local databases before seeding."""
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name

    if inspector.has_table("games"):
        game_columns = {col["name"] for col in inspector.get_columns("games")}
        if "price_cents" not in game_columns:
            if dialect == "sqlite":
                db.session.execute(text("ALTER TABLE games ADD COLUMN price_cents INTEGER NOT NULL DEFAULT 0"))
            elif dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE games ADD COLUMN IF NOT EXISTS price_cents INTEGER NOT NULL DEFAULT 0"
                    )
                )
            else:
                db.session.execute(text("ALTER TABLE games ADD COLUMN price_cents INTEGER"))
                db.session.execute(text("UPDATE games SET price_cents = 0 WHERE price_cents IS NULL"))

    if inspector.has_table("cafe_tables"):
        table_columns = {col["name"] for col in inspector.get_columns("cafe_tables")}
        if "price_cents" not in table_columns:
            if dialect == "sqlite":
                db.session.execute(
                    text("ALTER TABLE cafe_tables ADD COLUMN price_cents INTEGER NOT NULL DEFAULT 15000")
                )
            elif dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE cafe_tables ADD COLUMN IF NOT EXISTS price_cents INTEGER NOT NULL DEFAULT 15000"
                    )
                )
            else:
                db.session.execute(text("ALTER TABLE cafe_tables ADD COLUMN price_cents INTEGER"))
                db.session.execute(text("UPDATE cafe_tables SET price_cents = 15000 WHERE price_cents IS NULL"))

    if not inspector.has_table("admin_policies"):
        AdminPolicyDB.__table__.create(bind=db.engine)

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


def ensure_game_reservations_modern_schema() -> None:
    """Rebuild legacy game_reservations table if it still depends on table_reservation_id."""
    inspector = inspect(db.engine)
    if not inspector.has_table("game_reservations"):
        return

    columns = {col["name"] for col in inspector.get_columns("game_reservations")}
    if "table_reservation_id" not in columns:
        return

    dialect = db.engine.dialect.name
    if dialect != "sqlite":
        return

    db.session.execute(text("PRAGMA foreign_keys=OFF"))
    db.session.execute(text("ALTER TABLE game_reservations RENAME TO game_reservations_legacy"))

    db.session.execute(
        text(
            """
            CREATE TABLE game_reservations (
                id INTEGER PRIMARY KEY,
                booking_id INTEGER NOT NULL,
                game_copy_id INTEGER NOT NULL,
                requested_game_id INTEGER NOT NULL,
                CONSTRAINT uq_game_reservation_copy_per_booking UNIQUE (booking_id, game_copy_id),
                FOREIGN KEY(booking_id) REFERENCES bookings(id),
                FOREIGN KEY(game_copy_id) REFERENCES game_copies(id),
                FOREIGN KEY(requested_game_id) REFERENCES games(id)
            )
            """
        )
    )

    db.session.execute(text("DROP TABLE game_reservations_legacy"))
    db.session.execute(text("PRAGMA foreign_keys=ON"))
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
        {"table_nr": "T1", "capacity": 2, "price_cents": 12000, "floor": 1, "zone": "main", "status": "available"},
        {"table_nr": "T2", "capacity": 4, "price_cents": 15000, "floor": 1, "zone": "main", "status": "available"},
        {"table_nr": "T3", "capacity": 4, "price_cents": 16500, "floor": 1, "zone": "window", "status": "available"},
        {"table_nr": "T4", "capacity": 6, "price_cents": 21000, "floor": 2, "zone": "corner", "status": "available"},
        {"table_nr": "T5", "capacity": 8, "price_cents": 26000, "floor": 2, "zone": "main", "status": "available"},
        {"table_nr": "T6", "capacity": 4, "price_cents": 15000, "floor": 1, "zone": "bar", "status": "maintenance"},
        {"table_nr": "T7", "capacity": 6, "price_cents": 20000, "floor": 2, "zone": "window", "status": "available"},
        {"table_nr": "T8", "capacity": 2, "price_cents": 11000, "floor": 1, "zone": "bar", "status": "available"},
    ]

    existing = {t.table_nr: t for t in TableDB.query.all()}

    for table_data in table_seed:
        row = existing.get(table_data["table_nr"])
        if row is None:
            db.session.add(TableDB(**table_data))
            inserted += 1
            continue

        changed = False
        for field in ("capacity", "price_cents", "zone", "status"):
            if getattr(row, field) != table_data[field]:
                setattr(row, field, table_data[field])
                changed = True
        if getattr(row, "floor", None) != table_data["floor"]:
            row.floor = table_data["floor"]
            changed = True
        if changed:
            updated += 1

    return inserted, updated


def seed_admin_policy() -> tuple[int, int]:
    inserted = 0
    updated = 0

    row = db.session.get(AdminPolicyDB, 1)
    if row is None:
        db.session.add(
            AdminPolicyDB(
                id=1,
                booking_base_fee_cents=2500,
                booking_base_fee_priority=0,
                booking_base_fee_override_cents=None,
                booking_base_fee_override_priority=100,
                booking_base_fee_override_until_epoch=None,
                booking_cancel_time_limit_hours=24,
            )
        )
        inserted += 1
        return inserted, updated

    target_values = {
        "booking_base_fee_cents": 2500,
        "booking_base_fee_priority": 0,
        "booking_base_fee_override_cents": None,
        "booking_base_fee_override_priority": 100,
        "booking_base_fee_override_until_epoch": None,
        "booking_cancel_time_limit_hours": 24,
    }
    changed = False
    for key, value in target_values.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
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

    def _copy_code_prefix(title: str, game_id: int) -> str:
        normalized = unicodedata.normalize("NFKD", str(title or ""))
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^A-Z0-9]+", "-", ascii_only.upper()).strip("-")
        return slug or f"GAME{game_id}"

    # copy_idx→status override: index 2 = maintenance, index 3 = lost (per-game first title only)
    _special_status: dict[int, dict[int, str]] = {
        0: {3: "maintenance"},  # first game: copy 3 is in maintenance
        1: {3: "lost"},          # second game: copy 3 is lost
    }

    for game_idx, game in enumerate(games):
        prefix = _copy_code_prefix(game.title, game.id)
        copy_range = (1, 2, 3) if game_idx < 3 else (1, 2)  # first 3 games get 3 copies
        for copy_idx in copy_range:
            copy_code = f"{prefix}-{copy_idx:03d}"
            row = existing.get(copy_code)
            default_status = (
                _special_status.get(game_idx, {}).get(copy_idx, "available")
            )
            locations = ["shelf-a", "shelf-b", "shelf-c"]
            target = {
                "game_id": game.id,
                "copy_code": copy_code,
                "status": default_status,
                "location": locations[(copy_idx - 1) % len(locations)],
            }

            if row is None:
                db.session.add(GameCopyDB(**target))
                inserted += 1
                continue

            changed = False
            for field in ("game_id", "location"):
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


def _booking_seed_rows(now: datetime) -> list[dict]:
    td = now
    return [
        # ── Upcoming confirmed bookings ──────────────────────────────
        {
            "email": "a@a.a",
            "table_nr": "T2",
            "start_ts": (td + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0),
            "party_size": 4,
            "notes": "Demo booking with two game requests",
            "game_slots": [0, 1],
            "final_status": "confirmed",
        },
        {
            "email": "b@b.b",
            "table_nr": "T4",
            "start_ts": (td + timedelta(days=1)).replace(hour=19, minute=30, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=1)).replace(hour=21, minute=30, second=0, microsecond=0),
            "party_size": 5,
            "notes": "Demo booking with one game request",
            "game_slots": [2],
            "final_status": "confirmed",
        },
        {
            "email": "emma.hansen@example.com",
            "table_nr": "T7",
            "start_ts": (td + timedelta(days=2)).replace(hour=16, minute=0, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=2)).replace(hour=18, minute=30, second=0, microsecond=0),
            "party_size": 6,
            "notes": "Birthday group",
            "game_slots": [0, 2],
            "final_status": "confirmed",
        },
        {
            "email": "lars.olsen@example.com",
            "table_nr": "T3",
            "start_ts": (td + timedelta(days=3)).replace(hour=18, minute=0, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=3)).replace(hour=20, minute=0, second=0, microsecond=0),
            "party_size": 3,
            "notes": "Strategy game evening",
            "game_slots": [1, 3],
            "final_status": "confirmed",
        },
        # ── Currently seated (in progress) ───────────────────────────
        {
            "email": "sofie.berg@example.com",
            "table_nr": "T5",
            "start_ts": td.replace(hour=max(td.hour - 1, 0), minute=0, second=0, microsecond=0),
            "end_ts": td.replace(hour=min(td.hour + 1, 23), minute=30, second=0, microsecond=0),
            "party_size": 7,
            "notes": "Currently playing — demo seated booking",
            "game_slots": [0, 3],
            "final_status": "seated",
        },
        # ── Past completed bookings ───────────────────────────────────
        {
            "email": "a@a.a",
            "table_nr": "T1",
            "start_ts": (td - timedelta(days=3)).replace(hour=15, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=3)).replace(hour=17, minute=0, second=0, microsecond=0),
            "party_size": 2,
            "notes": "Past booking — completed",
            "game_slots": [3],
            "final_status": "completed",
        },
        {
            "email": "b@b.b",
            "table_nr": "T2",
            "start_ts": (td - timedelta(days=7)).replace(hour=19, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=7)).replace(hour=21, minute=0, second=0, microsecond=0),
            "party_size": 4,
            "notes": "Past booking — completed",
            "game_slots": [1, 2],
            "final_status": "completed",
        },
        {
            "email": "emma.hansen@example.com",
            "table_nr": "T4",
            "start_ts": (td - timedelta(days=14)).replace(hour=17, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=14)).replace(hour=19, minute=30, second=0, microsecond=0),
            "party_size": 5,
            "notes": "Past booking — completed",
            "game_slots": [0, 4],
            "final_status": "completed",
        },
        {
            "email": "jonas.vik@example.com",
            "table_nr": "T3",
            "start_ts": (td - timedelta(days=21)).replace(hour=18, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=21)).replace(hour=20, minute=0, second=0, microsecond=0),
            "party_size": 3,
            "notes": "Past booking — completed",
            "game_slots": [2],
            "final_status": "completed",
        },
        # ── Cancelled / no-show ───────────────────────────────────────
        {
            "email": "lars.olsen@example.com",
            "table_nr": "T1",
            "start_ts": (td - timedelta(days=5)).replace(hour=16, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=5)).replace(hour=18, minute=0, second=0, microsecond=0),
            "party_size": 2,
            "notes": "Past booking — cancelled by customer",
            "game_slots": [],
            "final_status": "cancelled",
        },
        {
            "email": "sofie.berg@example.com",
            "table_nr": "T2",
            "start_ts": (td - timedelta(days=10)).replace(hour=20, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=10)).replace(hour=22, minute=0, second=0, microsecond=0),
            "party_size": 4,
            "notes": "Past booking — no show",
            "game_slots": [1],
            "final_status": "no_show",
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

    now = datetime.now()
    seed_rows = _booking_seed_rows(now)

    existing_keys = {
        (row.customer_id, row.start_ts, row.end_ts)
        for row in BookingDB.query.order_by(BookingDB.id.asc()).all()
    }

    create_booking = get_create_booking_handler()

    _PAID_STATUSES = {"completed", "seated"}  # bookings that should show as paid
    _REFUNDED_STATUSES = {"cancelled", "no_show"}

    for row in seed_rows:
        customer = users_by_email.get(row["email"])
        # Skip tables in maintenance for new bookings
        table = tables_by_nr.get(row["table_nr"])
        if customer is None or table is None:
            continue
        if table.status == "maintenance" and row["final_status"] == "confirmed":
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

        # Advance booking to desired final status
        final = row["final_status"]
        if final != "confirmed":
            db_booking = db.session.get(BookingDB, booking.id)
            if db_booking is not None:
                db_booking.status = final

        # Adjust payment status to match reality
        if payment is not None:
            db_payment = db.session.get(PaymentDB, payment.id)
            if db_payment is not None:
                if final in _PAID_STATUSES:
                    db_payment.status = "paid"
                elif final in _REFUNDED_STATUSES:
                    db_payment.status = "refunded"
            inserted_payments += 1

        existing_keys.add(booking_key)

    return inserted_bookings, inserted_game_links, inserted_payments


def seed_incidents() -> int:
    """Seed one open and one resolved-ish incident on specific game copies."""
    inserted = 0

    steward = UserDB.query.filter_by(email="steward@example.com").first()
    if steward is None:
        return inserted

    copies = GameCopyDB.query.order_by(GameCopyDB.id.asc()).all()
    maintenance_copy = next((c for c in copies if c.status == "maintenance"), None)
    available_copy = next((c for c in copies if c.status == "available"), None)

    existing_copy_ids = {inc.game_copy_id for inc in IncidentDB.query.all()}

    # Open incident on the maintenance copy
    if maintenance_copy and maintenance_copy.id not in existing_copy_ids:
        db.session.add(IncidentDB(
            game_copy_id=maintenance_copy.id,
            reported_by=steward.id,
            incident_type="damage",
            note="Box corner torn, pieces intact. Needs new box.",
        ))
        existing_copy_ids.add(maintenance_copy.id)
        inserted += 1

    # A second incident on a different available copy (resolved by not blocking it)
    second_copy = next((c for c in copies if c.status == "available" and c != available_copy), None)
    if second_copy and second_copy.id not in existing_copy_ids:
        db.session.add(IncidentDB(
            game_copy_id=second_copy.id,
            reported_by=steward.id,
            incident_type="damage",
            note="Minor stain on board — still playable. Logged for tracking.",
        ))
        inserted += 1

    return inserted


def seed_waitlist() -> int:
    """Seed a few waitlist entries for testing."""
    inserted = 0

    users_by_email = {u.email: u for u in UserDB.query.all()}
    now = datetime.now()

    entries = [
        {"email": "jonas.vik@example.com", "party_size": 4, "notes": "Any table for Saturday evening"},
        {"email": "lars.olsen@example.com", "party_size": 2, "notes": "Window seat preferred"},
        {"email": "b@b.b", "party_size": 6, "notes": "Large group, floor 2 if possible"},
    ]

    existing_customer_ids = {w.customer_id for w in WaitlistDB.query.all()}

    for entry in entries:
        customer = users_by_email.get(entry["email"])
        if customer is None or customer.id in existing_customer_ids:
            continue
        db.session.add(WaitlistDB(
            customer_id=customer.id,
            party_size=entry["party_size"],
            notes=entry["notes"],
        ))
        existing_customer_ids.add(customer.id)
        inserted += 1

    return inserted


def seed_announcements() -> int:
    """Seed one published and one draft announcement."""
    inserted = 0

    admin = UserDB.query.filter_by(email="admin@example.com").first()
    if admin is None:
        return inserted

    now = datetime.now()
    existing_titles = {a.title for a in AnnouncementDB.query.all()}

    seeds = [
        {
            "title": "Grand Opening Weekend — Special Rates!",
            "body": "Join us this weekend for our grand opening celebration. All tables are 20% off and we have new games arriving Friday. Walk-ins welcome!",
            "cta_label": "Book a table",
            "cta_url": "/booking",
            "is_published": True,
            "published_at": now - timedelta(days=2),
            "created_by": admin.id,
        },
        {
            "title": "New Game Night — Every Thursday",
            "body": "Starting next month we're hosting a structured game night every Thursday at 18:00. Beginners welcome — stewards will guide you through the rules.",
            "cta_label": None,
            "cta_url": None,
            "is_published": False,
            "published_at": None,
            "created_by": admin.id,
        },
    ]

    for seed in seeds:
        if seed["title"] in existing_titles:
            continue
        db.session.add(AnnouncementDB(**seed))
        inserted += 1

    return inserted


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
        ensure_pricing_schema()
        ensure_booking_link_columns()
        ensure_game_reservations_modern_schema()
        clear_database()
        g_inserted, g_updated, g_total = seed_games()
        gt_inserted, gt_updated, gtl_inserted = seed_game_tags()
        t_inserted, t_updated = seed_tables()
        s_inserted, s_updated = seed_admin_policy()
        c_inserted, c_updated = seed_game_copies()
        u_inserted, u_updated = seed_users()
        b_inserted, bg_inserted, bp_inserted = seed_bookings()
        db.session.flush()
        i_inserted = seed_incidents()
        w_inserted = seed_waitlist()
        a_inserted = seed_announcements()

        db.session.commit()

        link_count, game_link_count, payment_count = _count_demo_records()

    print(
        "Demo data seeded: "
        f"games inserted={g_inserted}, updated={g_updated}, total={g_total}; "
        f"game-tags inserted={gt_inserted}, updated={gt_updated}, links inserted={gtl_inserted}; "
        f"tables inserted={t_inserted}, updated={t_updated}; "
        f"settings inserted={s_inserted}, updated={s_updated}; "
        f"copies inserted={c_inserted}, updated={c_updated}; "
        f"users inserted={u_inserted}, updated={u_updated}; "
        f"bookings inserted={b_inserted}, game-links inserted={bg_inserted}, payments inserted={bp_inserted}; "
        f"incidents inserted={i_inserted}; "
        f"waitlist inserted={w_inserted}; "
        f"announcements inserted={a_inserted}; "
        f"demo table-links total={link_count}, demo game-links total={game_link_count}, demo payments total={payment_count}"
    )


if __name__ == "__main__":
    seed_demo_data()
