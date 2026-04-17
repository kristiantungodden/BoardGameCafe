from flask_mail import Message
from flask import current_app

from shared.application.interface.email_service_interface import EmailServiceInterface

# Bruker EmailServiceInterface og vet kun hvordan en mail sendes. Ikke hvike type mail som skal sendes.
class FlaskMailService(EmailServiceInterface):
    def __init__(self, mail):
        self.mail = mail

    def _default_sender(self):
        sender = current_app.config.get("MAIL_DEFAULT_SENDER")
        return sender or "no-reply@localhost"
    
    def send_email(self, subject, sender, recipients, body):
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = body
        self.mail.send(msg)