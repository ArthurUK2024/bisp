"""Booking URLs."""

from django.urls import path

from .views import (
    BookingDetail,
    BookingListCreate,
    BookingPriceQuote,
    OwnerAnalyticsView,
)

urlpatterns = [
    path("", BookingListCreate.as_view()),
    path("quote/", BookingPriceQuote.as_view()),
    path("owner-analytics/", OwnerAnalyticsView.as_view()),
    path("<int:id>/", BookingDetail.as_view()),
]
