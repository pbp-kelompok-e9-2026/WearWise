from django.contrib import admin

from .forms import ClothingReferenceForm
from .models import ClothingReference


@admin.register(ClothingReference)
class ClothingReferenceAdmin(admin.ModelAdmin):
    form = ClothingReferenceForm
    list_display = ("clothing_name", "category", "price", "is_published", "updated_by", "updated_at")
    list_filter = ("is_published", "category", "material")
    search_fields = ("clothing_name", "brand", "source_name")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
