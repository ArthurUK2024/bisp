"""SRCH-04 — keep Listing.search_vector in sync with title + description.

Wired in apps.CatalogConfig.ready() so the signal connects on app load.
The post_save handler uses .filter(...).update() (not .save()) so it
does NOT trigger another post_save and recurse.
"""

from __future__ import annotations

from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Listing


@receiver(post_save, sender=Listing)
def update_listing_search_vector(sender, instance, created, **kwargs):
    Listing.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector("title", weight="A") + SearchVector("description", weight="B")
    )
