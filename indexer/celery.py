import os
from celery import Celery

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT")

CELERY_BROKER_URL = f"amqp://{RABBITMQ_HOST}:{RABBITMQ_PORT}"
CELERY_BACKEND_URL = f"rpc://{RABBITMQ_HOST}:{RABBITMQ_PORT}"

app = Celery('data-collector',
             broker=CELERY_BROKER_URL,
             backend=CELERY_BACKEND_URL,
             include=['indexer.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
)

app.conf.beat_schedule = {
    "update_validation_cycle": {
        "task": "indexer.tasks.update_validation_cycle",
        "schedule": 60.0
    },
    "update_elections": {
        "task": "indexer.tasks.update_elections",
        "schedule": 60.0
    },
    "update_complaints": {
        "task": "indexer.tasks.update_complaints",
        "schedule": 60.0
    }
}