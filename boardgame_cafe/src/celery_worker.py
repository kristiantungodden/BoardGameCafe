from app import create_app
from shared.infrastructure import celery, init_celery

# Create Flask app and bind Celery so tasks run with app context.
flask_app = create_app()
celery_app = init_celery(flask_app)

# Ensure task modules are imported when worker boots.
import shared.infrastructure.message_bus.event_tasks  # noqa: F401
