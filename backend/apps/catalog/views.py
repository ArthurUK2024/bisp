from decimal import Decimal, InvalidOperation

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    TrigramWordSimilarity,
)
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing, ListingPhoto
from .serializers import ListingPhotoSerializer, ListingSerializer
from .services import save_listing_photo, suggest_listing_from_photos

_UNIT_FIELD = {
    "hour": "price_hour",
    "day": "price_day",
    "month": "price_month",
}


class ListingListCreate(generics.ListCreateAPIView):
    serializer_class = ListingSerializer

    def get_queryset(self):
        params = self.request.query_params
        mine = params.get("mine")
        if mine and self.request.user.is_authenticated:
            return Listing.objects.filter(owner=self.request.user).prefetch_related("photos")

        qs = Listing.objects.filter(is_active=True).prefetch_related("photos")

        category = params.get("category")
        if category:
            qs = qs.filter(category=category)

        district = params.get("district")
        if district:
            qs = qs.filter(district=district)

        unit = params.get("unit")
        price_field = _UNIT_FIELD.get(unit)
        if price_field:
            qs = qs.exclude(**{f"{price_field}__isnull": True})

        for param, op in (("min_price", "gte"), ("max_price", "lte")):
            raw = params.get(param)
            if not raw:
                continue
            try:
                value = Decimal(raw)
            except (InvalidOperation, TypeError):
                continue
            field = price_field or "price_day"
            qs = qs.filter(**{f"{field}__{op}": value})

        q = params.get("q")
        if q:
            query = SearchQuery(q)
            qs = (
                qs.annotate(
                    rank=SearchRank("search_vector", query),
                    sim=TrigramWordSimilarity(q, "title"),
                )
                .filter(Q(search_vector=query) | Q(sim__gt=0.35) | Q(description__icontains=q))
                .order_by("-rank", "-sim", "-created_at")
            )

        return qs

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ListingDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ListingSerializer
    lookup_url_kwarg = "id"

    def get_queryset(self):
        if self.request.method == "GET":
            return Listing.objects.filter(is_active=True).prefetch_related("photos")
        return Listing.objects.filter(owner=self.request.user).prefetch_related("photos")

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        listing = self.get_object()
        listing.is_active = False
        listing.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingPhotoUpload(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, id):
        listing = get_object_or_404(Listing, pk=id, owner=request.user)
        uploaded = request.FILES.get("photo")
        if not uploaded:
            return Response({"photo": ["File required."]}, status=400)
        photo = save_listing_photo(listing, uploaded)
        return Response(ListingPhotoSerializer(photo).data, status=201)

    def delete(self, request, id, pk):
        listing = get_object_or_404(Listing, pk=id, owner=request.user)
        photo = get_object_or_404(ListingPhoto, pk=pk, listing=listing)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingAISuggest(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        files = request.FILES.getlist("photos") or list(request.FILES.values())
        if not files:
            return Response({"photos": ["At least one photo is required."]}, status=400)
        try:
            suggestion = suggest_listing_from_photos(files)
        except RuntimeError:
            return Response(
                {
                    "detail": (
                        "AI suggestions are not available right now. "
                        "Please fill the listing details manually."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(suggestion, status=200)
