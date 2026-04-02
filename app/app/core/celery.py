from celery import Celery

from app.core.config import settings

app = Celery(
    'app',
    backend=settings.celery_backend_url,
    broker=settings.celery_broker_url,
)
app.autodiscover_tasks(
    [
        "app.tasks.donate",
        "app.tasks.matrix",
        "app.tasks.bot",

    ]
)

app.conf.timezone = "Europe/Moscow"