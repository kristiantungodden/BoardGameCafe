from datetime import datetime, timezone

from features.bookings.domain.models.booking import Booking
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES


class BookingRepositoryContract:
    def get_repository(self):
        raise NotImplementedError("Subclasses must implement get_repository()")

    def test_save_booking_and_retrieve_by_id(self):
        repo = self.get_repository()

        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )

        saved = repo.save(booking)
        assert saved.id is not None

        retrieved = repo.get_by_id(saved.id)
        assert retrieved is not None
        assert retrieved.customer_id == 1

    def test_update_booking_status(self):
        repo = self.get_repository()
        booking = Booking(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            party_size=4,
        )
        saved = repo.save(booking)
        saved.confirm()
        saved.seat()
        updated = repo.update(saved)
        assert updated.status == "seated"

    def test_list_bookings_by_customer(self):
        repo = self.get_repository()
        repo.save(
            Booking(
                customer_id=1,
                start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
                end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
                party_size=4,
            )
        )
        repo.save(
            Booking(
                customer_id=1,
                start_ts=datetime(2026, 4, 11, 18, 0, tzinfo=timezone.utc),
                end_ts=datetime(2026, 4, 11, 20, 0, tzinfo=timezone.utc),
                party_size=2,
            )
        )
        repo.save(
            Booking(
                customer_id=2,
                start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
                end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
                party_size=6,
            )
        )

        customer1_bookings = repo.list_by_customer(1)
        assert len(customer1_bookings) == 2

    def test_find_overlapping_bookings(self):
        repo = self.get_repository()
        overlap_booking = repo.save(
            Booking(
                customer_id=1,
                start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
                end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
                party_size=4,
            )
        )
        repo.save(
            Booking(
                customer_id=1,
                start_ts=datetime(2026, 4, 10, 21, 0, tzinfo=timezone.utc),
                end_ts=datetime(2026, 4, 10, 23, 0, tzinfo=timezone.utc),
                party_size=4,
            )
        )

        overlapping = repo.find_overlapping_bookings(
            customer_id=1,
            start_ts=datetime(2026, 4, 10, 19, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 4, 10, 21, 0, tzinfo=timezone.utc),
            statuses=OVERLAP_BLOCKING_STATUSES,
        )

        assert any(b.id == overlap_booking.id for b in overlapping)
