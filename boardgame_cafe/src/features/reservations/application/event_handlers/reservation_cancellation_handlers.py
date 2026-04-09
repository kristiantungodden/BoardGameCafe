from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.infrastructure.message_bus import celery

@celery.task
def send_reservation_cancellation_email_task(recipient_email, reservation_details):
    mail_service = FlaskMailService()
    mail_service.send_reservation_cancellation_email(recipient_email, reservation_details)