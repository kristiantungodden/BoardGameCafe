from flask_mail import Message
from flask import current_app

class FlaskMailService:
    def __init__(self, mail):
        self.mail = mail

    def _default_sender(self):
        sender = current_app.config.get("MAIL_DEFAULT_SENDER")
        return sender or "no-reply@localhost"
    
    def send_email(self, subject, sender, recipients, body):
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = body
        self.mail.send(msg)
    
    def send_welcome_email(self, recipient_email):
        subject = "Welcome to BoardGame Cafe!"
        sender = self._default_sender()
        body = "Thank you for signing up at BoardGame Cafe!"
        self.send_email(subject, sender, [recipient_email], body)
    
    #reserservation_details må inneholde info om dato, tid, antall personer, osv.
    def send_reservation_confirmation_email(self, recipient_email, reservation_details):
        subject = "Your Reservation is Confirmed!"
        sender = self._default_sender()
        body = f"Hello,\n\nYour reservation has been confirmed.\n\nReservation Details:\n{reservation_details}\n\nWe look forward to seeing you at BoardGame Cafe!"
        self.send_email(subject, sender, [recipient_email], body)

    def send_reservation_reminder_email(self, recipient_email, reservation_details):
        subject = "Reservation Reminder"
        sender = self._default_sender()
        body = f"Hello,\n\nThis is a reminder for your upcoming reservation at BoardGame Cafe.\n\nReservation Details:\n{reservation_details}\n\nWe look forward to seeing you!"
        self.send_email(subject, sender, [recipient_email], body)
    
    def send_reservation_cancellation_email(self, recipient_email, reservation_details):
        subject = "Reservation Cancellation"
        sender = self._default_sender()
        body = f"Hello,\n\nYour reservation has been cancelled.\n\nReservation Details:\n{reservation_details}\n\nWe apologize for any inconvenience this may cause."
        self.send_email(subject, sender, [recipient_email], body)

    def send_password_reset_email(self, recipient_email, reset_link):
        subject = "Password Reset Request"
        sender = self._default_sender()
        body = f"Hello,\n\nYou have requested to reset your password.\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
        self.send_email(subject, sender, [recipient_email], body)
    