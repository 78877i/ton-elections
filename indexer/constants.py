import os

MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = int(os.getenv("MONGO_PORT"))
MONGO_DATABASE = os.getenv("MONGO_DATABASE")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD_FILE = os.getenv("MONGO_PASSWORD_FILE")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT")

CELERY_BROKER_URL = f"amqp://{RABBITMQ_HOST}:{RABBITMQ_PORT}"
CELERY_BACKEND_URL = f"rpc://{RABBITMQ_HOST}:{RABBITMQ_PORT}"

LITE_CLIENT_BINARY = 'distlib/lite-client'
LITE_CLIENT_CONFIG = 'liteserver_config.json'

