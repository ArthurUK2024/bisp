"""Common app views — health endpoint and shared utilities."""

import os

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Lightweight liveness probe.

    Returns 200 with the git SHA when the process is up and can serve a
    request. Used by compose healthcheck and by the Nuxt index page as a
    smoke test of the dual-URL runtimeConfig split.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "git_sha": os.environ.get("GIT_SHA", "unknown"),
            }
        )
