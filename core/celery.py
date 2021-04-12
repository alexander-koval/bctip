import os

import django
from celery import Celery

from bctip import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bctip.settings")
django.setup()

app = Celery('bctip')
app.config_from_object('bctip:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# @app.on_after_finalize.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(5.0, check_invoice_status.s(), name="check invoice status")
#
#
# @app.task
# def check_invoice_status():
#     from core import tasks
#     tasks.invoice_listener()
