"""Project URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.common.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/listings/", include("apps.catalog.urls")),
    path("api/v1/bookings/", include("apps.bookings.urls")),
    path("api/v1/", include("apps.payments.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
