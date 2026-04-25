from datetime import datetime, timedelta, timezone

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.game_rating_db import GameRatingDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db


def test_featured_picks_returns_top_rated_and_most_borrowed_last_month(client, app):
    now = datetime.now(timezone.utc)
    within_last_month = now - timedelta(days=10)

    with app.app_context():
        customer = UserDB(
            name="Featured Picks Customer",
            email="featured-picks-customer@example.com",
            password_hash="hashed",
            role="customer",
        )
        db.session.add(customer)
        db.session.flush()

        top_rated_game = GameDB(
            title="Top Rated Game",
            min_players=2,
            max_players=4,
            playtime_min=60,
            complexity=3.0,
        )
        most_borrowed_game = GameDB(
            title="Most Borrowed Game",
            min_players=2,
            max_players=6,
            playtime_min=45,
            complexity=2.0,
        )
        db.session.add_all([top_rated_game, most_borrowed_game])
        db.session.flush()

        db.session.add(
            GameRatingDB(
                customer_id=customer.id,
                game_id=top_rated_game.id,
                stars=5,
                comment="Excellent",
                created_at=within_last_month,
            )
        )

        for offset in range(2):
            booking = BookingDB(
                customer_id=customer.id,
                start_ts=within_last_month + timedelta(hours=offset),
                end_ts=within_last_month + timedelta(hours=offset + 2),
                party_size=2,
                status="confirmed",
            )
            db.session.add(booking)
            db.session.flush()
            db.session.add(
                GameReservationDB(
                    booking_id=booking.id,
                    game_copy_id=100 + offset,
                    requested_game_id=most_borrowed_game.id,
                )
            )

        db.session.commit()

    response = client.get("/api/games/featured-picks")
    assert response.status_code == 200

    payload = response.get_json()
    assert "top_rated_last_month" in payload
    assert "most_borrowed_last_month" in payload

    top_rated = payload["top_rated_last_month"]
    most_borrowed = payload["most_borrowed_last_month"]

    assert top_rated is not None
    assert top_rated["title"] == "Top Rated Game"
    assert most_borrowed is not None
    assert most_borrowed["title"] == "Most Borrowed Game"
