#Skal indikere at en reservasjon er blitt laget.
class ReservationCreated:
    def __init__(self, reservation_id):
        self.reservation_id = reservation_id

