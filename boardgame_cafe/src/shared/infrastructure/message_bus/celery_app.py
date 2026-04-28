from celery import Celery

celery = Celery(__name__, broker=None, backend=None)

def init_celery(app):
    celery.conf.broker_url = app.config["CELERY_BROKER_URL"]
    celery.conf.result_backend = app.config["CELERY_RESULT_BACKEND"]
    celery.conf.task_always_eager = bool(app.config.get("CELERY_TASK_ALWAYS_EAGER", False))
    celery.conf.task_eager_propagates = bool(app.config.get("CELERY_TASK_EAGER_PROPAGATES", False))
    celery.conf.update(app.config)  # optional for shared keys
    celery.conf.task_serializer = "json"
    celery.conf.accept_content = ["json"]
    celery.conf.result_serializer = "json"
    celery.conf.timezone = "UTC"
    celery.conf.broker_connection_retry_on_startup = False
    celery.conf.broker_connection_timeout = 1
    celery.conf.broker_transport_options = {
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    celery.autodiscover_tasks(
        ["shared.infrastructure.message_bus"],
        related_name="event_tasks",
    )
    return celery