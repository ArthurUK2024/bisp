"""ASGI config for the ijara project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ijara.settings")

application = get_asgi_application()
