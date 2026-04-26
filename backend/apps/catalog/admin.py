"""Catalog admin."""

from django.contrib import admin

from .models import Listing, ListingPhoto


class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0
    fields = ("sort_order", "image", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "category", "district", "is_active", "created_at")
    list_filter = ("category", "district", "is_active")
    search_fields = ("title", "description", "owner__email")
    inlines = [ListingPhotoInline]
    raw_id_fields = ("owner",)


@admin.register(ListingPhoto)
class ListingPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "sort_order", "uploaded_at")
    list_filter = ("uploaded_at",)
