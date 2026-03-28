from datetime import datetime, timedelta

from features.reservations.domain.models.reservation import TableReservation

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
