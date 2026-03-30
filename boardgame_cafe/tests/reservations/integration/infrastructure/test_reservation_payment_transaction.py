from datetime import datetime

import pytest

from features.reservations.application.use_cases.reservation_use_cases import CreateReservationCommand
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.user_db import UserDB
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
