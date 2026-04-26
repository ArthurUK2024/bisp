"""Booking serializers."""

from django.conf import settings
from rest_framework import serializers

from .models import Booking, BookingStateTransition


class BookingStateTransitionSerializer(serializers.ModelSerializer):
    actor_display_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingStateTransition
        fields = [
            "id",
            "from_state",
            "to_state",
            "actor",
            "actor_display_name",
            "reason",
            "created_at",
        ]

    def get_actor_display_name(self, obj):
        if obj.actor is None:
            return "system"
        profile = getattr(obj.actor, "profile", None)
        return profile.display_name if profile else obj.actor.email


class BookingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_category = serializers.CharField(source="listing.category", read_only=True)
    listing_district = serializers.CharField(source="listing.district", read_only=True)
    listing_photo = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source="listing.owner_id", read_only=True)
    owner_display_name = serializers.SerializerMethodField()
    renter_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "listing",
            "listing_title",
            "listing_category",
            "listing_district",
            "listing_photo",
            "owner_id",
            "owner_display_name",
            "renter",
            "renter_display_name",
            "start_at",
            "end_at",
            "state",
            "payment_method",
            "unit",
            "unit_price",
            "quantity",
            "total_amount",
            "note",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "renter",
            "state",
            "unit",
            "unit_price",
            "quantity",
            "total_amount",
            "created_at",
        ]

    def get_owner_display_name(self, obj):
        profile = getattr(obj.listing.owner, "profile", None)
        return profile.display_name if profile else ""

    def get_renter_display_name(self, obj):
        profile = getattr(obj.renter, "profile", None)
        return profile.display_name if profile else ""

    def get_listing_photo(self, obj):
        photo = obj.listing.photos.first()
        if not photo or not photo.image:
            return None
        return settings.MEDIA_HOST + photo.image.url


class BookingDetailSerializer(BookingSerializer):
    transitions = BookingStateTransitionSerializer(many=True, read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = BookingSerializer.Meta.fields + ["transitions"]
