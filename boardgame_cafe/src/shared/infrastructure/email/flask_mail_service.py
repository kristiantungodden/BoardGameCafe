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
    
    def send_welcome_email(self, recipient_email: str) -> None:
        """Send welcome email to new user."""
        self.send_email(
            subject="Welcome to Board Game Café",
            sender="noreply@boardgamecafe.com",
            recipients=[recipient_email],
            body="Welcome to Board Game Café! We're excited to have you."
        )
    
    def send_reservation_confirmation_email(self, recipient_email: str, reservation_details: str) -> None:
        """Send reservation confirmation email."""
        self.send_email(
            subject="Reservation Confirmed",
            sender="noreply@boardgamecafe.com",
            recipients=[recipient_email],
            body=f"Your reservation has been confirmed.\n\nDetails:\n{reservation_details}"
        )
    
    def send_reservation_reminder_email(self, recipient_email: str, reservation_details: str) -> None:
        """Send reservation reminder email."""
        self.send_email(
            subject="Reservation Reminder",
            sender="noreply@boardgamecafe.com",
            recipients=[recipient_email],
            body=f"Reminder: You have an upcoming reservation.\n\nDetails:\n{reservation_details}"
        )
    
    def send_reservation_cancellation_email(self, recipient_email: str, reservation_details: str) -> None:
        """Send reservation cancellation email."""
        self.send_email(
            subject="Reservation Cancelled",
            sender="noreply@boardgamecafe.com",
            recipients=[recipient_email],
            body=f"Your reservation has been cancelled.\n\nDetails:\n{reservation_details}"
        )
    
    def send_password_reset_email(self, recipient_email: str, reset_link: str) -> None:
        """Send password reset email."""
        self.send_email(
            subject="Password Reset Request",
            sender="noreply@boardgamecafe.com",
            recipients=[recipient_email],
            body=f"Click the link below to reset your password:\n\n{reset_link}"
        )

# --------------------------------------------------------------------------
# Celery tasks use the flask mail service to send emails asynchronously. 
# The tasks are defined in the features, bc they are closely related to the features that trigger them.
# --------------------------------------------------------------------------