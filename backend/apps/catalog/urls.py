"""Catalog URLs."""

from django.urls import path

from .views import ListingAISuggest, ListingDetail, ListingListCreate, ListingPhotoUpload

urlpatterns = [
    path("", ListingListCreate.as_view()),
    path("ai-suggest/", ListingAISuggest.as_view()),
    path("<int:id>/", ListingDetail.as_view()),
    path("<int:id>/photos/", ListingPhotoUpload.as_view()),
    path("<int:id>/photos/<int:pk>/", ListingPhotoUpload.as_view()),
]
