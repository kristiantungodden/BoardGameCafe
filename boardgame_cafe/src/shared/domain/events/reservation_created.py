#Skal indikere at en reservasjon er blitt laget.
class ReservationCreated:
    def __init__(self, reservation_id, user_id, user_email, table_numbers, start_ts, end_ts, party_size):
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.user_email = user_email
        self.table_numbers = table_numbers
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.party_size = party_size

