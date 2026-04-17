# Indicates a reservation payment has completed and confirmation can be sent.
class ReservationPaymentCompleted:
    def __init__(self, reservation_id, user_id, user_email, table_numbers, start_ts, end_ts, party_size):
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.user_email = user_email
        self.table_numbers = table_numbers
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.party_size = party_size
