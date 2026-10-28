from django import forms
from django.core.validators import MaxValueValidator

from .models import ClothingReference, PurchaseAnalysis


class PurchaseAnalysisForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SQLite accepts bigger integers than PostgreSQL's PositiveIntegerField.
        # Keep local validation consistent with the production database.
        self.fields["expected_wears"].validators.append(MaxValueValidator(2147483647))
        self.fields["expected_wears"].widget.attrs["max"] = 2147483647
        placeholders = {
            "clothing_name": "Contoh: kemeja untuk kuliah",
            "brand": "Contoh: merek favoritmu", "product_url": "https://…",
            "price": "300000", "budget": "400000", "expected_wears": "60",
            "target_cpw": "10000", "wears_per_month": "4", "weight_kg": "0.50",
        }
        for name, placeholder in placeholders.items():
            self.fields[name].widget.attrs["placeholder"] = placeholder
        for name in ("price", "budget", "target_cpw", "wears_per_month", "weight_kg"):
            self.fields[name].widget.attrs["inputmode"] = "decimal"
        self.fields["expected_wears"].widget.attrs["inputmode"] = "numeric"
        prompts = {
            "category": "Pilih jenis pakaian",
            "existing_clothing": "Pilih kondisi lemarimu",
            "purpose": "Pilih tujuan pemakaian",
            "material": "Pilih bahan utama",
        }
        for name, prompt in prompts.items():
            self.fields[name].choices = [("", prompt)] + [
                choice for choice in self.fields[name].choices if choice[0] != ""
            ]

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
        labels = {
            "clothing_name": "Pakaian apa yang kamu incar?",
            "existing_clothing": "Sudah punya yang serupa?", "purpose": "Mau dipakai untuk apa?",
            "price": "Harganya berapa? (Rp)", "budget": "Batas budget kamu (Rp)",
            "expected_wears": "Akan dipakai berapa kali?",
            "target_cpw": "Target biaya sekali pakai (Rp)",
            "wears_per_month": "Rencana pakai per bulan",
            "material": "Bahan utama", "weight_kg": "Berat pakaian (kg)",
        }
        help_texts = {
            "expected_wears": "Total selama kamu memilikinya. Misalnya 5 kali sebulan selama setahun = 60 kali.",
            "target_cpw": "Batas biaya yang menurutmu sepadan untuk sekali pemakaian.",
            "wears_per_month": "Untuk memperkirakan kapan targetmu tercapai.",
            "weight_kg": "Contoh: 500 gram = 0.50 kg. Isi bersama bahan utama.",
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


class ClothingReferenceForm(forms.ModelForm):
    class Meta:
        model = ClothingReference
        fields = (
            "clothing_name", "category", "brand", "product_url", "price",
            "material", "weight_kg", "source_name", "notes", "is_published",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "source_name": "Contoh: label produk, katalog merek, atau halaman toko. Cantumkan asal datanya.",
            "price": "Harga acuan; user tetap bisa mengubahnya saat membuat analisis.",
            "is_published": "Jika belum dicentang, data disimpan sebagai draft dan tidak terlihat oleh user.",
            "weight_kg": "Isi bersama bahan utama, atau kosongkan keduanya. Contoh: 500 gram = 0.50 kg.",
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("material") and cleaned.get("weight_kg") is None and "weight_kg" not in self.errors:
            self.add_error("weight_kg", "Isi berat pakaian atau kosongkan bahan utama.")
        if cleaned.get("weight_kg") is not None and not cleaned.get("material") and "material" not in self.errors:
            self.add_error("material", "Pilih bahan utama atau kosongkan berat pakaian.")
        return cleaned
