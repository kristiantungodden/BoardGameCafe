# Indicates a reservation was edited and stewardship views should be updated.
class ReservationUpdated:
    def __init__(
        self,
        reservation_id,
        user_id,
        table_numbers,
        start_ts,
        end_ts,
        party_size,
        updated_by_user_id,
        updated_by_role,
        notes,
    ):
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.table_numbers = table_numbers
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.party_size = party_size
        self.updated_by_user_id = updated_by_user_id
        self.updated_by_role = updated_by_role
        self.notes = notes
