from django.contrib import admin

from .models import CarbonEstimate, CategoryWeight, MaterialFactor


@admin.register(CarbonEstimate)
class CarbonEstimateAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "material", "weight_kg", "co2e_kg", "source", "updated_at")
    list_filter = ("material", "category", "source")
    search_fields = ("name", "user__username")


@admin.register(MaterialFactor)
class MaterialFactorAdmin(admin.ModelAdmin):
    list_display = ("material", "kg_co2e_per_kg", "updated_by", "updated_at")


@admin.register(CategoryWeight)
class CategoryWeightAdmin(admin.ModelAdmin):
    list_display = ("category", "weight_kg", "updated_by", "updated_at")
