from shared.infrastructure.email.flask_mail_service import FlaskMailService
from shared.infrastructure.message_bus import celery

@celery.task
def send_password_reset_email_task(recipient_email, reset_link):
    mail_service = FlaskMailService()
    mail_service.send_password_reset_email(recipient_email, reset_link)

# --------------------------------------------------------------------------
# Celery task is in features, because it is closely related to user features.
# --------------------------------------------------------------------------