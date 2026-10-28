from django.contrib import admin
from .models import ConditionRecord

@admin.register(ConditionRecord)
class ConditionRecordAdmin(admin.ModelAdmin):
    list_display = ("item", "user", "condition", "recommendation", "status", "created_at")
    list_filter = ("condition", "recommendation", "status")