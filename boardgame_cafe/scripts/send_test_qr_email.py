"""
send_test_qr_email.py — Developer tool to send one real QR confirmation email.

Finds a confirmed booking in the database, overrides the recipient address
with the one you provide, and delivers the full HTML email with QR attachment
synchronously (no Celery worker required).

Usage:
    python scripts/send_test_qr_email.py --email you@example.com
    python scripts/send_test_qr_email.py --email you@example.com --booking-id 3
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import create_app
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure.message_bus.event_tasks import send_reservation_confirmation_email


def _find_confirmed_booking(booking_id: int | None) -> BookingDB | None:
    if booking_id is not None:
        return BookingDB.query.filter_by(id=booking_id, status="confirmed").first()
    return (
        BookingDB.query.filter_by(status="confirmed")
        .order_by(BookingDB.start_ts.asc())
        .first()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test QR confirmation email.")
    parser.add_argument("--email", required=True, help="Recipient email address")
    parser.add_argument("--booking-id", type=int, default=None, help="Specific booking ID to use")
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        booking = _find_confirmed_booking(args.booking_id)
        if booking is None:
            sys.exit(
                "No confirmed booking found. "
                "Run the seeder first (python scripts/seed_demo_data.py) "
                "or pass --booking-id with a valid confirmed booking."
            )

        user = UserDB.query.get(booking.customer_id)
        if user is None:
            sys.exit(f"User with id={booking.customer_id} not found.")

        # Collect table numbers via the table_reservation join table
        table_rows = (
            TableReservationDB.query
            .filter_by(booking_id=booking.id)
            .all()
        )
        table_numbers = [
            TableDB.query.get(tr.table_id).table_nr
            for tr in table_rows
            if TableDB.query.get(tr.table_id) is not None
        ]
        if not table_numbers:
            # Fallback: use the table linked directly on the booking row
            direct_table = TableDB.query.get(booking.table_id)
            if direct_table:
                table_numbers = [direct_table.table_nr]

        event_payload = {
            "data": {
                "reservation_id": booking.id,
                "user_id": user.id,
                "user_email": args.email,  # override — send to developer address
                "table_numbers": table_numbers,
                "start_ts": booking.start_ts.strftime("%Y-%m-%d %H:%M") if booking.start_ts else "",
                "end_ts": booking.end_ts.strftime("%Y-%m-%d %H:%M") if booking.end_ts else "",
                "party_size": booking.party_size,
            }
        }

        print(
            f"Sending QR confirmation for booking #{booking.id} "
            f"(tables: {', '.join(table_numbers) or '-'}, "
            f"start: {event_payload['data']['start_ts']}) "
            f"→ {args.email}"
        )

        # apply() runs synchronously in-process — no Celery worker needed
        result = send_reservation_confirmation_email.apply(args=[event_payload])
        if result.failed():
            print(f"ERROR: Task failed — {result.result}")
            sys.exit(1)

        print("Done. Check your inbox.")


if __name__ == "__main__":
    main()
