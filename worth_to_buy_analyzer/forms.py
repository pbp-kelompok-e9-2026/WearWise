from django import forms
from django.core.validators import MaxValueValidator

from .models import PurchaseAnalysis


class PurchaseAnalysisForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SQLite accepts bigger integers than PostgreSQL's PositiveIntegerField.
        # Keep local validation consistent with the production database.
        self.fields["expected_wears"].validators.append(MaxValueValidator(2147483647))
        self.fields["expected_wears"].widget.attrs["max"] = 2147483647

    class Meta:
        model = PurchaseAnalysis
        # Explicit allowlist: ownership, score version and carbon snapshots are
        # always controlled by the server, never by submitted form fields.
        fields = (
            "clothing_name", "category", "brand", "product_url",
            "existing_clothing", "purpose", "price", "budget",
            "expected_wears", "target_cpw", "wears_per_month",
            "material", "weight_kg",
        )
        help_texts = {
            "expected_wears": "Perkiraan total pemakaian selama pakaian dimiliki, bukan per bulan.",
            "wears_per_month": "Opsional, untuk memperkirakan waktu mencapai target biaya per pakai.",
            "material": "Isi bersama berat jika ingin menyertakan estimasi karbon dari modul Carbon Footprint.",
            "weight_kg": "Masukkan berat dalam kg. Jika material dan berat kosong, data karbon belum tersedia.",
        }

    def clean(self):
        cleaned = super().clean()
        material = cleaned.get("material")
        weight = cleaned.get("weight_kg")
        if material and weight is None and "weight_kg" not in self.errors:
            self.add_error("weight_kg", "Isi berat pakaian untuk menghitung estimasi karbon.")
        if weight is not None and not material and "material" not in self.errors:
            self.add_error("material", "Pilih material pakaian untuk menghitung estimasi karbon.")
        return cleaned


class DecisionForm(forms.ModelForm):
    class Meta:
        model = PurchaseAnalysis
        fields = ("decision", "decision_note")
        widgets = {"decision_note": forms.Textarea(attrs={"rows": 3})}
