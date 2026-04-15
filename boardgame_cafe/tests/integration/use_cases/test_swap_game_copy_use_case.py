from datetime import datetime, timedelta

from shared.infrastructure import db
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.games.infrastructure.repositories.game_copy_repository import GameCopyRepositoryImpl
from features.reservations.infrastructure.repositories.game_reservation_repository import SqlAlchemyGameReservationRepository
from features.reservations.application.use_cases.reservation_game_use_cases import SwapGameCopyUseCase
from features.games.infrastructure.database.game_copy_db import GameCopyDB


def test_swap_success(client, app, test_data):
    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.utcnow()
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2)
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

        copy_a = test_data["copies"][0]["id"]
        copy_b = test_data["copies"][1]["id"]
        requested_game = test_data["games"][0]["id"]

        rg = GameReservationDB(booking_id=reservation_id, game_copy_id=copy_a, requested_game_id=requested_game)
        db.session.add(rg)
        db.session.commit()
        reservation_game_id = rg.id

        # run use case
        use_case = SwapGameCopyUseCase(game_copy_repo=GameCopyRepositoryImpl(), game_reservation_repo=SqlAlchemyGameReservationRepository())
        new_rg = use_case.execute(reservation_game_id, copy_b)

        assert new_rg.game_copy_id == copy_b

        # verify statuses
        old = db.session.get(GameCopyDB, copy_a)
        new = db.session.get(GameCopyDB, copy_b)
        assert old.status == "available"
        assert new.status == "reserved"


def test_swap_missing_reservation_game(client, app, test_data):
    use_case = SwapGameCopyUseCase(game_copy_repo=GameCopyRepositoryImpl(), game_reservation_repo=SqlAlchemyGameReservationRepository())
    try:
        use_case.execute(999999, 1)
        assert False, "Expected ValueError for missing reservation_game"
    except ValueError:
        pass


def test_swap_missing_new_copy(client, app, test_data):
    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.utcnow()
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2)
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

        copy_a = test_data["copies"][0]["id"]
        requested_game = test_data["games"][0]["id"]

        rg = GameReservationDB(booking_id=reservation_id, game_copy_id=copy_a, requested_game_id=requested_game)
        db.session.add(rg)
        db.session.commit()
        reservation_game_id = rg.id

    use_case = SwapGameCopyUseCase(game_copy_repo=GameCopyRepositoryImpl(), game_reservation_repo=SqlAlchemyGameReservationRepository())
    try:
        use_case.execute(reservation_game_id, 999999)
        assert False, "Expected ValueError for missing new copy"
    except ValueError:
        pass
