from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .constants import CATEGORY_CHOICES, MATERIAL_CHOICES
from .services import SOURCE_CLIMATIQ, SOURCE_FALLBACK, sustainability_score


class CarbonEstimate(models.Model):
    SOURCE_CHOICES = [(SOURCE_CLIMATIQ, "Climatiq"), (SOURCE_FALLBACK, "Offline estimate")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carbon_estimates")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    material = models.CharField(max_length=30, choices=MATERIAL_CHOICES)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])
    estimated_wears = models.PositiveIntegerField(default=30, validators=[MinValueValidator(1)])
    co2e_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0, editable=False)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_FALLBACK, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return f"{self.name} ({self.co2e_kg} kg CO2e)"

    @property
    def cost_per_wear(self):
        if self.price is None:
            return None
        return float(self.price) / self.estimated_wears

    @property
    def score(self):
        return sustainability_score(self.co2e_kg, self.estimated_wears)


class MaterialFactor(models.Model):
    """Faktor emisi per material (kg CO2e per kg kain) yang diatur analyzer.

    Kalau baris untuk sebuah material tidak ada, aplikasi memakai nilai bawaan
    di constants.py. Jadi tabel ini hanya berisi nilai yang diubah analyzer.
    """

    material = models.CharField(max_length=30, choices=MATERIAL_CHOICES, unique=True)
    kg_co2e_per_kg = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["material"]

    def __str__(self):
        return f"{self.material}: {self.kg_co2e_per_kg} kg CO2e/kg"


class CategoryWeight(models.Model):
    """Berat rata-rata per kategori pakaian (kg) yang diatur analyzer."""

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, unique=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category"]

    def __str__(self):
        return f"{self.category}: {self.weight_kg} kg"
