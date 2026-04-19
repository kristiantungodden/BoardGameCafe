# Indicates a reservation was seated and stewardship views should be updated.
class ReservationSeated:
    def __init__(
        self,
        reservation_id,
        user_id,
        table_numbers,
        start_ts,
        end_ts,
        party_size,
        seated_by_user_id,
        seated_by_role,
    ):
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.table_numbers = table_numbers
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.party_size = party_size
        self.seated_by_user_id = seated_by_user_id
        self.seated_by_role = seated_by_role