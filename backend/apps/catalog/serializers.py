"""Catalog serializers."""

from django.conf import settings
from rest_framework import serializers

from .models import Listing, ListingPhoto


class ListingPhotoSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ListingPhoto
        fields = ["id", "image", "sort_order"]

    def get_image(self, obj):
        if not obj.image:
            return None
        return settings.MEDIA_HOST + obj.image.url


class ListingSerializer(serializers.ModelSerializer):
    photos = ListingPhotoSerializer(many=True, read_only=True)
    owner_id = serializers.IntegerField(read_only=True)
    owner_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "owner_id",
            "owner_display_name",
            "title",
            "description",
            "category",
            "district",
            "price_hour",
            "price_day",
            "price_month",
            "is_active",
            "photos",
            "created_at",
        ]
        read_only_fields = ["id", "owner_id", "is_active", "created_at"]

    def get_owner_display_name(self, obj):
        profile = getattr(obj.owner, "profile", None)
        return profile.display_name if profile else ""

    def validate(self, attrs):
        if not (attrs.get("price_hour") or attrs.get("price_day") or attrs.get("price_month")):
            raise serializers.ValidationError("At least one price is required.")
        return attrs
