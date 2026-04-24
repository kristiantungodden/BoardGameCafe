from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.reservations.infrastructure.repositories.reservation_repository import (
	SqlAlchemyReservationRepository,
)
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.user_db import UserDB


def _create_user_table_game(db_session):
	user = UserDB(
		role="customer",
		name="Test User",
		email="reservation-invariants@test.local",
		password_hash="hash",
	)
	table = TableDB(table_nr="T99", capacity=4, zone="main", status="available")
	game = GameDB(
		title="Invariant Test Game",
		min_players=2,
		max_players=4,
		playtime_min=60,
		complexity=Decimal("1.50"),
	)
	db_session.add_all([user, table, game])
	db_session.commit()

	copy = GameCopyDB(
		game_id=game.id,
		copy_code="INV-COPY-1",
		status="available",
	)
	db_session.add(copy)
	db_session.commit()
	return user, table, game, copy


def test_table_reservation_db_rejects_invalid_time_window(db_session):
	user, _, _, _ = _create_user_table_game(db_session)

	row = BookingDB(
		customer_id=user.id,
		start_ts=datetime(2026, 4, 1, 19, 0),
		end_ts=datetime(2026, 4, 1, 18, 0),
		party_size=4,
		status="confirmed",
	)

	db_session.add(row)
	with pytest.raises(IntegrityError):
		db_session.commit()
	db_session.rollback()


def test_table_reservation_db_rejects_invalid_status(db_session):
	user, _, _, _ = _create_user_table_game(db_session)

	row = BookingDB(
		customer_id=user.id,
		start_ts=datetime(2026, 4, 1, 18, 0),
		end_ts=datetime(2026, 4, 1, 20, 0),
		party_size=4,
		status="draft",
	)

	db_session.add(row)
	with pytest.raises(IntegrityError):
		db_session.commit()
	db_session.rollback()


def test_game_reservation_db_rejects_duplicate_copy_for_same_booking(db_session):
	user, table, game, copy = _create_user_table_game(db_session)

	booking = BookingDB(
		customer_id=user.id,
		start_ts=datetime(2026, 4, 1, 18, 0),
		end_ts=datetime(2026, 4, 1, 20, 0),
		party_size=4,
		status="confirmed",
	)
	db_session.add(booking)
	db_session.commit()

	table_link = TableReservationDB(booking_id=booking.id, table_id=table.id)
	db_session.add(table_link)
	db_session.commit()

	first = GameReservationDB(
		booking_id=booking.id,
		game_copy_id=copy.id,
		requested_game_id=game.id,
	)
	db_session.add(first)
	db_session.commit()

	duplicate = GameReservationDB(
		booking_id=booking.id,
		game_copy_id=copy.id,
		requested_game_id=game.id,
	)
	db_session.add(duplicate)
	with pytest.raises(IntegrityError):
		db_session.commit()
	db_session.rollback()


def test_reservation_repository_returns_all_linked_table_ids(db_session):
	user, table_one, _, _ = _create_user_table_game(db_session)
	table_two = TableDB(table_nr="T100", capacity=2, zone="main", status="available")
	db_session.add(table_two)
	db_session.commit()

	booking = BookingDB(
		customer_id=user.id,
		start_ts=datetime(2026, 4, 1, 18, 0),
		end_ts=datetime(2026, 4, 1, 20, 0),
		party_size=6,
		status="confirmed",
	)
	db_session.add(booking)
	db_session.commit()

	db_session.add_all(
		[
			TableReservationDB(booking_id=booking.id, table_id=table_one.id),
			TableReservationDB(booking_id=booking.id, table_id=table_two.id),
		]
	)
	db_session.commit()

	repo = SqlAlchemyReservationRepository(session=db_session)
	reservation = repo.get_by_id(booking.id)

	assert reservation is not None
	assert reservation.table_id == table_one.id
	assert reservation.table_ids == [table_one.id, table_two.id]
