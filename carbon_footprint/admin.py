from django.contrib import admin

from .models import CarbonEstimate


@admin.register(CarbonEstimate)
class CarbonEstimateAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "material", "weight_kg", "co2e_kg", "source", "updated_at")
    list_filter = ("material", "category", "source")
    search_fields = ("name", "user__username")
