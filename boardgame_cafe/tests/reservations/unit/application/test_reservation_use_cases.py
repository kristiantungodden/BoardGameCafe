from datetime import datetime

from features.reservations.application.use_cases.reservation_use_cases import (
    CreateReservationCommand,
    CreateReservationUseCase,
)


class FakeReservationRepo:
    def __init__(self):
        self.items = []
        self.next_id = 1

    def add(self, reservation):
        reservation.id = self.next_id
        self.next_id += 1
        self.items.append(reservation)
        return reservation

    def get_by_id(self, reservation_id):
        for item in self.items:
            if item.id == reservation_id:
                return item
        return None

    def list_all(self):
        return self.items

    def list_for_table_in_window(self, table_id, start_ts, end_ts):
        return [
            r for r in self.items
            if r.table_id == table_id and r.start_ts < end_ts and start_ts < r.end_ts
        ]

    def update(self, reservation):
        return reservation


def test_create_reservation_from_customer_order():
    repo = FakeReservationRepo()
    use_case = CreateReservationUseCase(repo)

    cmd = CreateReservationCommand(
        customer_id=1,
        table_id=2,
        start_ts=datetime(2026, 3, 30, 18, 0),
        end_ts=datetime(2026, 3, 30, 20, 0),
        party_size=4,
        notes="Bursdag",
    )

    reservation = use_case.execute(cmd)

    assert reservation.id == 1
    assert reservation.customer_id == 1
    assert reservation.table_id == 2
    assert reservation.party_size == 4
    assert reservation.notes == "Bursdag"
    assert reservation.status == "confirmed"