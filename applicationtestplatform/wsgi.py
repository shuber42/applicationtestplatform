"""WSGI entry point for the applicationtestplatform project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "applicationtestplatform.settings")

application = get_wsgi_application()
