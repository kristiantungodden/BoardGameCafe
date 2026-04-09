#Skal holde info om at en bruker har registrert seg.

class UserRegistered:
    def __init__(self, user_id, email):
        self.user_id = user_id
        self.email = email # Fjerne email slik at handler finner info via user_id.