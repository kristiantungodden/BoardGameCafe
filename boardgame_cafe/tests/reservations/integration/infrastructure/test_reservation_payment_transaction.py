from datetime import datetime

import pytest

from features.reservations.application.use_cases.reservation_use_cases import CreateReservationCommand
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.user_db import UserDB
from shared.domain.exceptions import ValidationError
from shared.presentation.api import deps


def test_transaction_rolls_back_reservation_when_payment_creation_fails(app, monkeypatch):
    from shared.infrastructure import db

    with app.app_context():
        user = UserDB(
            role="customer",
            name="Txn User",
            email="txn-fail@test.local",
            password_hash="hash",
        )
        table = TableDB(table_nr="TXN-1", capacity=4, zone="main", status="available")
        db.session.add_all([user, table])
        db.session.commit()

        def failing_create_and_save_payment(reservation, repository):
            raise ValueError("Payment provider unavailable")

        monkeypatch.setattr(deps, "create_and_save_payment", failing_create_and_save_payment)

        handler = deps.get_create_reservation_with_payment_handler()

        with pytest.raises(ValueError):
            handler(
                CreateReservationCommand(
                    customer_id=user.id,
                    table_id=table.id,
                    start_ts=datetime(2026, 4, 2, 18, 0),
                    end_ts=datetime(2026, 4, 2, 20, 0),
                    party_size=4,
                )
            )

        assert db.session.query(TableReservationDB).count() == 0


def test_atomic_booking_rolls_back_when_game_selection_fails(app):
    from shared.infrastructure import db

    with app.app_context():
        user = UserDB(
            role="customer",
            name="Txn User",
            email="txn-game-fail@test.local",
            password_hash="hash",
        )
        table = TableDB(table_nr="TXN-2", capacity=4, zone="main", status="available")
        game = GameDB(
            title="Catan",
            min_players=3,
            max_players=4,
            playtime_min=90,
            complexity=2.5,
            description="Trade and build",
            image_url="https://example.test/catan.png",
        )
        db.session.add_all([user, table, game])
        db.session.flush()

        copy = GameCopyDB(
            game_id=game.id,
            copy_code="TXN-GAME-1",
            condition_note="Good",
            status="available",
            location="Shelf A",
        )
        db.session.add(copy)
        db.session.commit()

        handler = deps.get_create_booking_handler()

        with pytest.raises(ValidationError):
            handler(
                CreateReservationCommand(
                    customer_id=user.id,
                    table_id=table.id,
                    start_ts=datetime(2026, 4, 3, 18, 0),
                    end_ts=datetime(2026, 4, 3, 20, 0),
                    party_size=4,
                ),
                games=[
                    {"requested_game_id": game.id, "game_copy_id": copy.id},
                    {"requested_game_id": game.id, "game_copy_id": copy.id},
                ],
            )

        assert db.session.query(TableReservationDB).count() == 0
        assert db.session.query(PaymentDB).count() == 0
