#Her skal vi koble domain og infrastructure sammen for å sende email når en reservasjon er laget eller en bruker har registrert seg.
from shared.application.interface import EmailServiceInterface
from shared.domain.events import UserRegistered, ReservationCreated

def send_welcome_email(event: UserRegistered, email_service: EmailServiceInterface):
    email_service.send_welcome_email(event.email)

# Denne testen sjekker den henter riktig data fra repoet og sender en email med riktige detaljer.
# Foreløpig er det et fake repo og en dummy email service for å isolere testen til event handleren.
def send_reservation_confirmation_email(event: ReservationCreated, email_service: EmailServiceInterface, reservation_repo, user_repo):
    reservation = reservation_repo.get_by_id(event.reservation_id)
    if reservation is None:
        return  # or log error
    user = user_repo.get_by_id(reservation.customer_id)
    if user is None:
        return  # or log error
    reservation_details = (
        f"Table {reservation.table_id}, "
        f"{reservation.start_ts.isoformat()} to {reservation.end_ts.isoformat()}, "
        f"party size {reservation.party_size}"
    )
    if reservation.notes:
        reservation_details += f", notes: {reservation.notes}"
    email_service.send_reservation_confirmation_email(user.email, reservation_details)

# Denne testen registerer event handlers for både UserRegistered og ReservationCreated, 
# og sjekker at de blir kalt når eventene publisher.
def register_email_event_handlers(event_bus, email_service, reservation_repo, user_repo):

    def welcome_handler(event):
        send_welcome_email(event, email_service)

    def reservation_handler(event):
        send_reservation_confirmation_email(event, email_service, reservation_repo, user_repo)

    event_bus.subscribe(UserRegistered, welcome_handler)
    event_bus.subscribe(ReservationCreated, reservation_handler)