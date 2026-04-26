"""WSGI config for the ijara project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ijara.settings")

application = get_wsgi_application()
