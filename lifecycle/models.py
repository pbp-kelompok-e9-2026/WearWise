from django.db import models
import uuid
from django.contrib.auth.models import User

from wardrobe.models import ClothingItem

class ConditionRecord(models.Model):
    class Condition(models.TextChoices):
        GOOD = "good", "Masih bagus"
        MINOR = "minor", "Rusak ringan"
        MAJOR = "major", "Rusak berat"
        WORN_OUT = "worn_out", "Tidak layak pakai"

    class Recommendation(models.TextChoices):
        REPAIR = "repair", "Repair"
        REUSE = "reuse", "Reuse"
        RECYCLE = "recycle", "Recycle"

    class Status(models.TextChoices):
        PENDING = "pending", "Belum ditindaklanjuti"
        IN_PROGRESS = "in_progress", "Sedang dikerjakan"
        DONE = "done", "Selesai"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="condition_records")
    item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE, related_name="condition_records")
    condition = models.CharField(max_length=20, choices=Condition.choices)
    damage_description = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    recommendation = models.CharField(max_length=20, choices=Recommendation.choices, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item.name} - {self.get_condition_display()}"