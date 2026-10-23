from decimal import Decimal

from django import forms

from .constants import CATEGORY_WEIGHT_KG
from .models import CarbonEstimate
from .services import compute_co2e


class CarbonEstimateForm(forms.ModelForm):
    class Meta:
        model = CarbonEstimate
        fields = ["name", "category", "material", "weight_kg", "price", "estimated_wears"]
        labels = {
            "name": "Item name",
            "weight_kg": "Weight (kg)",
            "price": "Price in Rupiah (optional)",
            "estimated_wears": "Estimated wears",
        }
        help_texts = {
            "weight_kg": "Leave empty to use the average weight for the category.",
            "price": "Drives the Climatiq estimate and cost per wear. Without a price, the footprint is estimated from weight and material.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["weight_kg"].required = False
        for field in self.fields.values():
            css = "cf-input cf-select" if isinstance(field.widget, forms.Select) else "cf-input"
            field.widget.attrs["class"] = css
        self.fields["weight_kg"].widget.attrs.update({"step": "0.01", "min": "0.01"})
        self.fields["price"].widget.attrs.update({"step": "any", "min": "0"})
        self.fields["estimated_wears"].widget.attrs.update({"min": "1"})

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if cleaned.get("weight_kg") is None and category in CATEGORY_WEIGHT_KG:
            cleaned["weight_kg"] = Decimal(str(CATEGORY_WEIGHT_KG[category]))
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Hitung ulang emisi hanya untuk data baru atau kalau material, berat, atau harga
        # berubah, supaya edit nama atau jumlah wears tidak memanggil API lagi.
        if not obj.pk or {"material", "category", "weight_kg", "price"} & set(self.changed_data):
            obj.co2e_kg, obj.source = compute_co2e(obj.material, obj.weight_kg, obj.price)
        if commit:
            obj.save()
        return obj
