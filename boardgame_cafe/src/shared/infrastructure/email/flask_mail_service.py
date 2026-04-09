from .. import celery
from flask_mail import Message
from ...application.interface.email_service_interface import EmailServiceInterface
class FlaskMailService(EmailServiceInterface):

    def __init__(self, mail):
        self.mail = mail
    
    def send_email(self, subject, sender, recipients, body):
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = body
        self.mail.send(msg)

# --------------------------------------------------------------------------
# Celery tasks use the flask mail service to send emails asynchronously. 
# The tasks are defined in the features, bc they are closely related to the features that trigger them.
# --------------------------------------------------------------------------