from datetime import datetime, timedelta

from features.reservations.domain.models.reservation import TableReservation
from shared.domain.exceptions import InvalidStatusTransition

# Just a simple test to use as a template for future tests 
def test_reservation_seat_changes_status_to_seated():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = TableReservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	reservation.seat()

	assert reservation.status == "seated"


def test_reservation_complete_changes_status_to_completed():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = TableReservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	reservation.seat()
	reservation.complete()

	assert reservation.status == "completed"


def test_reservation_no_show_changes_status_to_no_show():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = TableReservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	reservation.mark_no_show()

	assert reservation.status == "no_show"


def test_reservation_cannot_complete_without_being_seated():
	start = datetime(2026, 3, 23, 18, 0)
	end = start + timedelta(hours=2)
	reservation = TableReservation(
		customer_id=1,
		table_id=10,
		start_ts=start,
		end_ts=end,
		party_size=4,
	)

	try:
		reservation.complete()
		assert False, "Expected InvalidStatusTransition"
	except InvalidStatusTransition:
		assert True
