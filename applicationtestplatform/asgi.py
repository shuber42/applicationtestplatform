"""ASGI entry point for the applicationtestplatform project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "applicationtestplatform.settings")

application = get_asgi_application()
