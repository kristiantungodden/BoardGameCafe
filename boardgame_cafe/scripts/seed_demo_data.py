import os
import re
import sys
import unicodedata
from decimal import Decimal
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import create_app
from features.bookings.application.use_cases.booking_lifecycle_use_cases import BookingCommand
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.game_rating_db import GameRatingDB
from features.games.infrastructure.database.game_tag_db import GameTagDB
from features.games.infrastructure.database.game_tag_link_db import GameTagLinkDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.reservations.composition.reservation_use_case_factories import get_create_booking_handler
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.admin_policy_db import AdminPolicyDB
from features.users.infrastructure.database.announcement_db import AnnouncementDB
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db
from shared.domain.exceptions import ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

SEED_GAMES = [
    {
        "title": "Ticket to Ride",
        "min_players": 2,
        "max_players": 5,
        "playtime_min": 120,
        "price_cents": 6900,
        "complexity": Decimal("2.00"),
        "description": "Train routes",
        "image_url": "https://www.outland.no/media/catalog/product/cache/ab0d362431b8ede7989b9ba1a279c0de/8/2/824968717028__c6eeffe288fa356b83f091672c4a4c7c.jpg",
    },
    {
        "title": "Yatzy",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 60,
        "price_cents": 2500,
        "complexity": Decimal("1.20"),
        "description": "Dice rolling game",
        "image_url": "https://play-lh.googleusercontent.com/VTvOurV1NLn_M_2PAuicV-HqSbpbgmhKOIff9EcNj1Oj1dm7EF5APUKHMeLUncnHPbs",
    },
    {
        "title": "Catan",
        "min_players": 2,
        "max_players": 4,
        "playtime_min": 180,
        "price_cents": 7900,
        "complexity": Decimal("2.30"),
        "description": "Srategy resource game",
        "image_url": "https://image.api.playstation.com/vulcan/ap/rnd/202209/2812/yzsrapB7edp44te4uowFz62i.png",
    },
    {
        "title": "Monopoly",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 240,
        "price_cents": 3900,
        "complexity": Decimal("1.60"),
        "description": "Money handling",
        "image_url": "https://www.ringo.no/wp-content/uploads/2025/10/802073_6-880x880.jpg",
    },
    {
        "title": "Chutes and Ladders",
        "min_players": 2,
        "max_players": 4,
        "playtime_min": 40,
        "price_cents": 1900,
        "complexity": Decimal("1.00"),
        "description": "Dice rolling game",
        "image_url": "https://d189539ycils2q.cloudfront.net/media/catalog/product/e/g/egmont-stigespill-damm-15033.jpg",
    },
    {
        "title": "Secret Hitler",
        "min_players": 5,
        "max_players": 10,
        "playtime_min": 60,
        "price_cents": 5900,
        "complexity": Decimal("2.50"),
        "description": "Secret Hitler is a fast-paced social deduction party game for 5-10 players about political intrigue and betrayal in 1930s Germany",
        "image_url": "https://www.outland.no/media/catalog/product/7/1/711746875073__a45f93c3df2f3fcff01ff924782e4a4c.jpg",
    },
    {
        "title": "Ligretto",
        "min_players": 2,
        "max_players": 12,
        "playtime_min": 15,
        "price_cents": 2200,
        "complexity": Decimal("1.30"),
        "description": "Ligretto is a fast-paced, chaotic, and easy-to-learn card game for 2-12 players (depending on combined sets) where everyone plays simultaneously to discard their cards. Players aim to empty their personal 10-card \"Ligretto\" deck into communal piles on the table sorted by color (1-10) before anyone else.",
        "image_url": "https://pricespy-75b8.kxcdn.com/product/standard/280/393659.jpg",
    },
    {
        "title": "UNO",
        "min_players": 2,
        "max_players": 10,
        "playtime_min": 10,
        "price_cents": 1800,
        "complexity": Decimal("1.10"),
        "description": "Uno is the highly popular card game played by millions around the globe. This game is played by matching and then discarding the cards in one's hand till none are left. Since its inception, there are now many versions of Uno that one can play. Here are the rules of the original or classic Uno.",
        "image_url": "https://www.lirumlarumleg.no/cdn/shop/files/Uno.jpg?v=1748880659",
    },
    {
        "title": "Risk",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 240,
        "price_cents": 5200,
        "complexity": Decimal("2.30"),
        "description": "Risk is a classic turn-based strategy board game of military conquest and diplomacy, usually for 2 to 6 players. Players control armies and attempt to take over the world by capturing all 42 territories across six continents, or by achieving a secret, specific mission. Battles are decided through dice rolls.",
        "image_url": "https://d189539ycils2q.cloudfront.net/media/catalog/product/r/i/risk-brettspill.jpg",
    },
    {
        "title": "Trivial Pursuit",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 60,
        "price_cents": 4300,
        "complexity": Decimal("1.70"),
        "description": "Each player has a circular playing piece with six pie-shaped holes. The goal of the game is to collect a pie in each color. the colors correspond to different question categories. The board consists of a circular track with spaces in seven different colors.",
        "image_url": "https://static.partyking.org/fit-in/1300x0/products/original/trivial-pursuit-master-edition-2.jpg",
    },
    {
        "title": "Scrabble",
        "min_players": 2,
        "max_players": 4,
        "playtime_min": 60,
        "price_cents": 3400,
        "complexity": Decimal("2.10"),
        "description": "Scrabble is a classic crossword-style word game for 2-4 players, where participants create words on a 15x15 grid using letter tiles with varying point values. Players compete for the highest score by placing tiles on premium squares to multiply points, aiming to maximize score through vocabulary and strategic placement.",
        "image_url": "https://img.joomcdn.net/9ea28c4c84b9d605888ff02512256e13a66c9275_original.jpeg",
    },
    {
        "title": "Othello",
        "min_players": 2,
        "max_players": 2,
        "playtime_min": 30,
        "price_cents": 2700,
        "complexity": Decimal("1.80"),
        "description": "Othello is a two-player strategy board game played on an 8x8 grid with 64 reversible discs, black on one side and white on the other. The objective is to have the majority of discs showing your color when the last playable empty square is filled, often by capturing opponent pieces through surrounding them (\"outflanking\").",
        "image_url": "https://www.lekolar.no/globalassets/inriver/resources/16796_46068.jpg",
    },
    {
        "title": "Chess",
        "min_players": 2,
        "max_players": 2,
        "playtime_min": 30,
        "price_cents": 3100,
        "complexity": Decimal("2.80"),
        "description": "Chess is a two-player strategic board game played on a 64-square, 8x8 checkered board. Each player commands 16 pieces-one king, one queen, two rooks, two bishops, two knights, and eight pawns-with the objective to checkmate the opponent's king, placing it under inevitable threat of capture.",
        "image_url": "https://www.regencychess.co.uk/images/RCPB232.jpg",
    },
    {
        "title": "7 Wonders",
        "min_players": 3,
        "max_players": 7,
        "playtime_min": 30,
        "price_cents": 6100,
        "complexity": Decimal("2.20"),
        "description": "Three decks of cards featuring images of historical civilizations, armed conflicts, and commercial activity are used in the card drafting game 7 Wonders.",
        "image_url": "https://gamezone.no/Media/Cache/Images/7/9/WEB_Image_7_Wonders_Brettspill_-_Norsk_Grunnspill__sev_front913413104_plid_74499.jpeg?v=639120565944370000",
    },
]


def seed_games() -> tuple[int, int, int]:
    inserted = 0
    updated = 0

    existing_games = {game.title: game for game in db.session.query(GameDB).all()}

    for game_data in SEED_GAMES:
        existing = existing_games.get(game_data["title"])
        if existing is None:
            db.session.add(GameDB(**game_data))
            inserted += 1
            continue

        changed = False
        for field in (
            "min_players",
            "max_players",
            "playtime_min",
            "price_cents",
            "complexity",
            "description",
            "image_url",
        ):
            if getattr(existing, field) != game_data[field]:
                setattr(existing, field, game_data[field])
                changed = True

        if changed:
            updated += 1

    total = db.session.query(GameDB).count()
    return inserted, updated, total


def _build_demo_users() -> list[dict]:
    now = datetime.now()
    users: list[dict] = [
        # Customers
        {
            "role": "customer",
            "name": "Emma Hansen",
            "email": "emma.hansen@example.com",
            "phone": "+4791234567",
            "password": "Password1!",
            "created_at": now - timedelta(days=240),
        },
        {
            "role": "customer",
            "name": "Lars Olsen",
            "email": "lars.olsen@example.com",
            "phone": "+4798765432",
            "password": "Password1!",
            "created_at": now - timedelta(days=210),
        },
        {
            "role": "customer",
            "name": "Sofie Berg",
            "email": "sofie.berg@example.com",
            "phone": None,
            "password": "Password1!",
            "created_at": now - timedelta(days=180),
        },
        {
            "role": "customer",
            "name": "Jonas Vik",
            "email": "jonas.vik@example.com",
            "phone": "+4792345678",
            "password": "Password1!",
            "created_at": now - timedelta(days=160),
        },
        # Staff
        {
            "role": "staff",
            "name": "steward",
            "email": "steward@example.com",
            "phone": None,
            "password": "StewardPw1!",
            "created_at": now - timedelta(days=340),
        },
        {
            "role": "staff",
            "name": "Maria Lund",
            "email": "maria.lund@example.com",
            "phone": "+4745678901",
            "password": "StewardPw1!",
            "created_at": now - timedelta(days=260),
        },
        # Admin
        {
            "role": "admin",
            "name": "Adam Admin",
            "email": "admin@example.com",
            "phone": None,
            "password": "AdminPw123!",
            "created_at": now - timedelta(days=365),
        },
    ]

    # Extra historical customers to create a meaningful registration trend line.
    for idx in range(1, 25):
        users.append(
            {
                "role": "customer",
                "name": f"Report User {idx:02d}",
                "email": f"report.user{idx:02d}@example.com",
                "phone": None,
                "password": "Password1!",
                "created_at": now - timedelta(days=max(5, 350 - idx * 13)),
            }
        )

    return users


DEMO_USERS = _build_demo_users()


DEMO_GAME_TAGS = {
    "strategy": ["Ticket to Ride", "Catan", "7 Wonders", "Risk", "Chess"],
    "family": ["Yatzy", "Monopoly", "UNO", "Scrabble", "Trivial Pursuit"],
    "party": ["Secret Hitler", "UNO", "Ligretto"],
    "quick-play": ["Yatzy", "Ligretto", "UNO", "Othello"],
}


def clear_database() -> None:
    """Remove all rows so the seed starts from an empty database."""
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


def seed_tables() -> tuple[int, int]:
    inserted = 0
    updated = 0

    table_seed = [
        # Floor 1 - Main area
        {"table_nr": "T1", "capacity": 2, "price_cents": 12000, "floor": 1, "zone": "main", "status": "available"},
        {"table_nr": "T2", "capacity": 4, "price_cents": 15000, "floor": 1, "zone": "main", "status": "available"},
        {"table_nr": "T3", "capacity": 4, "price_cents": 16500, "floor": 1, "zone": "main", "status": "available"},
        {"table_nr": "T4", "capacity": 6, "price_cents": 18000, "floor": 1, "zone": "main", "status": "available"},
        # Floor 1 - Window area
        {"table_nr": "T5", "capacity": 2, "price_cents": 13500, "floor": 1, "zone": "window", "status": "available"},
        {"table_nr": "T6", "capacity": 4, "price_cents": 16500, "floor": 1, "zone": "window", "status": "available"},
        # Floor 1 - Bar area
        {"table_nr": "T7", "capacity": 2, "price_cents": 11000, "floor": 1, "zone": "bar", "status": "available"},
        {"table_nr": "T8", "capacity": 4, "price_cents": 15000, "floor": 1, "zone": "bar", "status": "maintenance"},
        # Floor 2 - Main area
        {"table_nr": "T9", "capacity": 6, "price_cents": 20000, "floor": 2, "zone": "main", "status": "available"},
        {"table_nr": "T10", "capacity": 8, "price_cents": 25000, "floor": 2, "zone": "main", "status": "available"},
        {"table_nr": "T11", "capacity": 4, "price_cents": 16500, "floor": 2, "zone": "main", "status": "available"},
        # Floor 2 - Corner area
        {"table_nr": "T12", "capacity": 6, "price_cents": 21000, "floor": 2, "zone": "corner", "status": "available"},
        {"table_nr": "T13", "capacity": 8, "price_cents": 26000, "floor": 2, "zone": "corner", "status": "available"},
        # Floor 2 - Window area
        {"table_nr": "T14", "capacity": 4, "price_cents": 17000, "floor": 2, "zone": "window", "status": "available"},
        {"table_nr": "T15", "capacity": 6, "price_cents": 20000, "floor": 2, "zone": "window", "status": "available"},
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
                booking_base_fee_override_cents=None,
                booking_base_fee_override_until_epoch=None,
                booking_cancel_time_limit_hours=24,
            )
        )
        inserted += 1
        return inserted, updated

    target_values = {
        "booking_base_fee_cents": 2500,
        "booking_base_fee_override_cents": None,
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
                    created_at=user_data.get("created_at"),
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
        target_created_at = user_data.get("created_at")
        if target_created_at is not None and row.created_at != target_created_at:
            row.created_at = target_created_at
            changed = True

        if changed:
            updated += 1

    return inserted, updated


def _booking_seed_rows(now: datetime) -> list[dict]:
    td = now
    # Keep the seeded "currently seated" booking inside opening hours (09:00-23:00).
    seated_start = td.replace(
        hour=max(min(td.hour - 1, 21), 9), minute=0, second=0, microsecond=0
    )
    seated_end = seated_start + timedelta(hours=2)
    rows = [
        # ── Upcoming confirmed bookings (next 1-7 days) ──────────────────────────────
        {
            "email": "emma.hansen@example.com",
            "table_nr": "T15",
            "start_ts": (td + timedelta(days=2)).replace(hour=16, minute=0, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=2)).replace(hour=18, minute=30, second=0, microsecond=0),
            "party_size": 6,
            "notes": "Birthday group celebration",
            "game_slots": [0, 2],
            "final_status": "confirmed",
            "created_at": td - timedelta(days=3),
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
            "created_at": td - timedelta(days=2),
        },
        {
            "email": "sofie.berg@example.com",
            "table_nr": "T10",
            "start_ts": (td + timedelta(days=4)).replace(hour=17, minute=30, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=4)).replace(hour=20, minute=0, second=0, microsecond=0),
            "party_size": 7,
            "notes": "Weekend gaming session",
            "game_slots": [0, 3],
            "final_status": "confirmed",
        },
        {
            "email": "ingrid.andersen@example.com",
            "table_nr": "T5",
            "start_ts": (td + timedelta(days=5)).replace(hour=14, minute=0, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=5)).replace(hour=16, minute=0, second=0, microsecond=0),
            "party_size": 2,
            "notes": "Afternoon gaming",
            "game_slots": [2],
            "final_status": "confirmed",
        },
        {
            "email": "magnus.kristensen@example.com",
            "table_nr": "T12",
            "start_ts": (td + timedelta(days=6)).replace(hour=18, minute=30, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=6)).replace(hour=21, minute=0, second=0, microsecond=0),
            "party_size": 6,
            "notes": "Board game tournament",
            "game_slots": [1, 4],
            "final_status": "confirmed",
        },
        {
            "email": "nora.solstad@example.com",
            "table_nr": "T6",
            "start_ts": (td + timedelta(days=7)).replace(hour=19, minute=0, second=0, microsecond=0),
            "end_ts": (td + timedelta(days=7)).replace(hour=21, minute=0, second=0, microsecond=0),
            "party_size": 4,
            "notes": "Casual Friday night",
            "game_slots": [0],
            "final_status": "confirmed",
        },
        # ── Currently seated (in progress) ───────────────────────────
        {
            "email": "erik.svendsen@example.com",
            "table_nr": "T1",
            "start_ts": seated_start,
            "end_ts": seated_end,
            "party_size": 2,
            "notes": "Currently playing — demo seated booking",
            "game_slots": [1],
            "final_status": "seated",
            "created_at": td - timedelta(days=1),
        },
        # ── Past completed bookings ───────────────────────────────────
        {
            "email": "emma.hansen@example.com",
            "table_nr": "T9",
            "start_ts": (td - timedelta(days=14)).replace(hour=17, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=14)).replace(hour=19, minute=30, second=0, microsecond=0),
            "party_size": 5,
            "notes": "Past booking — completed",
            "game_slots": [0, 4],
            "final_status": "completed",
            "created_at": td - timedelta(days=17),
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
            "created_at": td - timedelta(days=23),
        },
        {
            "email": "lars.olsen@example.com",
            "table_nr": "T12",
            "start_ts": (td - timedelta(days=2)).replace(hour=17, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=2)).replace(hour=19, minute=0, second=0, microsecond=0),
            "party_size": 3,
            "notes": "Past booking — completed",
            "game_slots": [1],
            "final_status": "completed",
        },
        # ── Cancelled / no-show ───────────────────────────────────────
        {
            "email": "sofie.berg@example.com",
            "table_nr": "T11",
            "start_ts": (td - timedelta(days=5)).replace(hour=16, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=5)).replace(hour=18, minute=0, second=0, microsecond=0),
            "party_size": 4,
            "notes": "Past booking — cancelled by customer",
            "game_slots": [],
            "final_status": "cancelled",
            "created_at": td - timedelta(days=8),
        },
        {
            "email": "ingrid.andersen@example.com",
            "table_nr": "T2",
            "start_ts": (td - timedelta(days=10)).replace(hour=20, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=10)).replace(hour=22, minute=0, second=0, microsecond=0),
            "party_size": 4,
            "notes": "Past booking — no show",
            "game_slots": [1],
            "final_status": "no_show",
            "created_at": td - timedelta(days=12),
        },
        {
            "email": "magnus.kristensen@example.com",
            "table_nr": "T15",
            "start_ts": (td - timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0),
            "end_ts": (td - timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0),
            "party_size": 2,
            "notes": "Past booking — completed",
            "game_slots": [3],
            "final_status": "completed",
        },
    ]

    # Historical timeline data for reports (revenue + most booked games).
    timeline_users = [
        "emma.hansen@example.com",
        "lars.olsen@example.com",
        "sofie.berg@example.com",
        "jonas.vik@example.com",
    ] + [f"report.user{i:02d}@example.com" for i in range(1, 25)]
    table_cycle = ["T1", "T2", "T3", "T4", "T5", "T7", "T8"]
    table_capacity = {
        "T1": 2,
        "T2": 4,
        "T3": 4,
        "T4": 6,
        "T5": 8,
        "T7": 6,
        "T8": 2,
    }

    for idx in range(1, 61):
        day_ago = 5 + idx * 5  # spans roughly 10 months
        table_nr = table_cycle[idx % len(table_cycle)]
        capacity = table_capacity[table_nr]
        party_size = max(2, min(capacity, 2 + (idx % 4)))
        start = (td - timedelta(days=day_ago)).replace(
            hour=12 + (idx % 7), minute=0, second=0, microsecond=0
        )
        end = start + timedelta(hours=2)
        created_at = start - timedelta(days=(idx % 4) + 1)

        if idx % 13 == 0:
            final_status = "cancelled"
        elif idx % 11 == 0:
            final_status = "no_show"
        else:
            final_status = "completed"

        # Game 0 and 1 are requested most frequently to make "most booked" visible.
        if idx % 2 == 0:
            game_slots = [0, 1]
        elif idx % 3 == 0:
            game_slots = [0, 2]
        elif idx % 5 == 0:
            game_slots = [1, 3]
        else:
            game_slots = [1]

        rows.append(
            {
                "email": timeline_users[idx % len(timeline_users)],
                "table_nr": table_nr,
                "start_ts": start,
                "end_ts": end,
                "party_size": party_size,
                "notes": f"Historical booking #{idx:02d}",
                "game_slots": game_slots,
                "final_status": final_status,
                "created_at": created_at,
            }
        )

    return rows


def seed_bookings() -> tuple[int, int, int]:
    inserted_bookings = 0
    inserted_game_links = 0
    inserted_payments = 0
    skipped = 0

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

    _PAID_STATUSES = {"confirmed", "completed", "seated"}
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

        try:
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
        except ValidationError:
            skipped += 1
            continue
        inserted_bookings += 1
        inserted_game_links += len(reservation_games)

        db_booking = db.session.get(BookingDB, booking.id)
        if db_booking is not None and row.get("created_at") is not None:
            db_booking.created_at = row["created_at"]

        # Advance booking to desired final status (created is only transient pre-payment)
        final = row["final_status"]
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
                if row.get("created_at") is not None:
                    db_payment.created_at = row["created_at"]
            inserted_payments += 1

        existing_keys.add(booking_key)

    if skipped:
        print(f"Skipped {skipped} booking seeds due to availability/capacity validation.")
    return inserted_bookings, inserted_game_links, inserted_payments


def seed_game_ratings() -> int:
    inserted = 0

    games = GameDB.query.order_by(GameDB.id.asc()).all()
    customers = (
        UserDB.query.filter(UserDB.role == "customer")
        .order_by(UserDB.id.asc())
        .all()
    )
    if not games or not customers:
        return inserted

    existing = {
        (row.customer_id, row.game_id)
        for row in GameRatingDB.query.order_by(GameRatingDB.id.asc()).all()
    }

    now = datetime.now()
    top_game_ids = [g.id for g in games[: min(3, len(games))]]

    for idx, customer in enumerate(customers):
        # Every customer rates one "top" game to make report trends obvious.
        top_game_id = top_game_ids[idx % len(top_game_ids)]
        top_key = (customer.id, top_game_id)
        if top_key not in existing:
            stars = 5 if idx % 3 != 0 else 4
            db.session.add(
                GameRatingDB(
                    customer_id=customer.id,
                    game_id=top_game_id,
                    stars=stars,
                    comment="Great for café sessions.",
                    created_at=now - timedelta(days=(idx * 7) % 330 + 1),
                )
            )
            existing.add(top_key)
            inserted += 1

        # Secondary rating to diversify averages.
        secondary_game = games[(idx + 2) % len(games)]
        secondary_key = (customer.id, secondary_game.id)
        if secondary_key not in existing:
            stars = 4 if (idx % 4) else 3
            db.session.add(
                GameRatingDB(
                    customer_id=customer.id,
                    game_id=secondary_game.id,
                    stars=stars,
                    comment="Solid pick.",
                    created_at=now - timedelta(days=(idx * 5) % 300 + 2),
                )
            )
            existing.add(secondary_key)
            inserted += 1

    return inserted


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
        clear_database()
        g_inserted, g_updated, g_total = seed_games()
        gt_inserted, gt_updated, gtl_inserted = seed_game_tags()
        t_inserted, t_updated = seed_tables()
        s_inserted, s_updated = seed_admin_policy()
        c_inserted, c_updated = seed_game_copies()
        u_inserted, u_updated = seed_users()
        b_inserted, bg_inserted, bp_inserted = seed_bookings()
        gr_inserted = seed_game_ratings()
        db.session.flush()
        i_inserted = seed_incidents()
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
        f"game-ratings inserted={gr_inserted}; "
        f"incidents inserted={i_inserted}; "
        f"announcements inserted={a_inserted}; "
        f"demo table-links total={link_count}, demo game-links total={game_link_count}, demo payments total={payment_count}"
    )


if __name__ == "__main__":
    seed_demo_data()
