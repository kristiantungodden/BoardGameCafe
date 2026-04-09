from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.infrastructure.message_bus import celery

@celery.task
def send_welcome_email_task(recipient_email):
    mail_service = FlaskMailService()
    mail_service.send_welcome_email(recipient_email)

# --------------------------------------------------------------------------
# Celery task is in features, because it is closely related to user features.
# --------------------------------------------------------------------------