# Indicates a reservation was completed and stewardship views should be updated.
class ReservationCompleted:
    def __init__(
        self,
        reservation_id,
        user_id,
        table_numbers,
        start_ts,
        end_ts,
        party_size,
        completed_by_user_id,
        completed_by_role,
    ):
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.table_numbers = table_numbers
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.party_size = party_size
        self.completed_by_user_id = completed_by_user_id
        self.completed_by_role = completed_by_role