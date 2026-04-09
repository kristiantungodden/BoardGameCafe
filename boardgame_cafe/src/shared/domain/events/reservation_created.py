#Skal indikere at en reservasjon er blitt laget.
class ReservationCreated:
    def __init__(self, reservation_id, user_id, user_email, reservation_details):
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.user_email = user_email
        self.reservation_details = reservation_details

