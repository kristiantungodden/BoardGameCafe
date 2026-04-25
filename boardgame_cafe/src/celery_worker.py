from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Worker only needs app context + task registry; keep boot resilient if Stripe key is absent.
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder_worker_only")

from app import create_app
from shared.infrastructure import init_celery

# Create Flask app and bind Celery so tasks run with app context.
flask_app = create_app()
celery_app = init_celery(flask_app)

# Ensure task modules are imported when worker boots.
import shared.infrastructure.message_bus.event_tasks
