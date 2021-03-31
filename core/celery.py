import os

import django
from celery import Celery

from bctip import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bctip.settings")
django.setup()

app = Celery('bctip')
app.config_from_object('bctip:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
