"""Add SearchVectorField + GIN index to Listing (SRCH-04).

Backfills the vector for any rows already in place. New rows are kept
fresh by apps.catalog.signals.update_listing_search_vector.
"""

import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations


def backfill_search_vector(apps, schema_editor):
    Listing = apps.get_model("catalog", "Listing")
    Listing.objects.update(
        search_vector=django.contrib.postgres.search.SearchVector(
            "title", weight="A"
        )
        + django.contrib.postgres.search.SearchVector("description", weight="B")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(
                blank=True, null=True
            ),
        ),
        migrations.AddIndex(
            model_name="listing",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["search_vector"], name="catalog_search_vector_gin"
            ),
        ),
        migrations.RunPython(backfill_search_vector, migrations.RunPython.noop),
    ]
