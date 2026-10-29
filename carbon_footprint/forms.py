from decimal import Decimal

from django import forms

from .constants import (
    CATEGORY_CHOICES,
    CATEGORY_WEIGHT_KG,
    FALLBACK_DEFAULT_KG_CO2E_PER_KG,
    FALLBACK_KG_CO2E_PER_KG,
    MATERIAL_CHOICES,
)
from .models import CarbonEstimate, CategoryWeight, MaterialFactor
from .services import (
    SOURCE_FALLBACK,
    _to_decimal,
    category_weight,
    compute_co2e,
    current_category_weights,
    current_material_rates,
)


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
        default_weight = category_weight(category)
        if cleaned.get("weight_kg") is None and default_weight is not None:
            cleaned["weight_kg"] = Decimal(str(default_weight))
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


def _dec(value):
    return Decimal(str(round(value, 2)))


class FactorsForm(forms.Form):
    """Form analyzer untuk mengatur faktor emisi per material dan berat per kategori."""

    recalculate = forms.BooleanField(
        required=False,
        label="Hitung ulang estimasi offline yang sudah ada dengan nilai baru",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        rates = current_material_rates()
        weights = current_category_weights()
        self.material_rows = self._build("material", MATERIAL_CHOICES, rates, FALLBACK_KG_CO2E_PER_KG, 7)
        self.category_rows = self._build("category", CATEGORY_CHOICES, weights, CATEGORY_WEIGHT_KG, 6)

    def _build(self, prefix, choices, current, defaults, max_digits):
        rows = []
        for key, label in choices:
            name = f"{prefix}_{key}"
            default = _dec(defaults[key])
            self.fields[name] = forms.DecimalField(
                label=label,
                min_value=Decimal("0.01"),
                max_digits=max_digits,
                decimal_places=2,
                initial=_dec(current.get(key, defaults.get(key, FALLBACK_DEFAULT_KG_CO2E_PER_KG))),
                widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "data-default": str(default)}),   # gaya field dari .wtb-field (ruang Analyzer)
            )
            current_value = _dec(current.get(key, defaults.get(key, FALLBACK_DEFAULT_KG_CO2E_PER_KG)))
            rows.append({"key": key, "field": self[name], "default": default, "changed": current_value != default})
        return rows

    def save(self, user):
        """Simpan hanya nilai yang berbeda dari bawaan; nilai yang kembali ke bawaan menghapus barisnya."""
        for row in self.material_rows:
            self._apply(MaterialFactor, "material", row["key"], "kg_co2e_per_kg", row["field"].name, row["default"], user)
        for row in self.category_rows:
            self._apply(CategoryWeight, "category", row["key"], "weight_kg", row["field"].name, row["default"], user)
        return self._recalculate() if self.cleaned_data["recalculate"] else 0

    def _apply(self, model, key_field, key, value_field, form_field, default, user):
        value = self.cleaned_data[form_field]
        if value == default:
            model.objects.filter(**{key_field: key}).delete()
        else:
            model.objects.update_or_create(**{key_field: key}, defaults={value_field: value, "updated_by": user})

    @staticmethod
    def _recalculate():
        """Hitung ulang estimasi offline saja. Hasil Climatiq dibiarkan karena tidak memakai tabel ini."""
        rates = current_material_rates()
        items = list(CarbonEstimate.objects.filter(source=SOURCE_FALLBACK))
        for obj in items:
            rate = rates.get(obj.material, FALLBACK_DEFAULT_KG_CO2E_PER_KG)
            obj.co2e_kg = _to_decimal(float(obj.weight_kg) * rate)
        CarbonEstimate.objects.bulk_update(items, ["co2e_kg"])
        return len(items)


def reset_factors():
    """Hapus semua nilai buatan analyzer, kembali ke bawaan constants.py."""
    MaterialFactor.objects.all().delete()
    CategoryWeight.objects.all().delete()
