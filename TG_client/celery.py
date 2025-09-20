import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TG_client.settings")

app = Celery("TG_client")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()