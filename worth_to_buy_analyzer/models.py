from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, URLValidator
from django.db import models


class PurchaseAnalysis(models.Model):
    class Category(models.TextChoices):
        TOP = "top", "Atasan"
        BOTTOM = "bottom", "Bawahan"
        OUTER = "outer", "Jaket / outerwear"
        DRESS = "dress", "Dress / pakaian terusan"
        OTHER = "other", "Lainnya"

    class ExistingClothing(models.TextChoices):
        USABLE = "usable", "Ada dan masih layak"
        REPAIRABLE = "repairable", "Ada tetapi perlu diperbaiki"
        NONE = "none", "Belum ada"

    class Purpose(models.TextChoices):
        ROUTINE = "routine", "Kebutuhan rutin"
        REPLACEMENT = "replacement", "Mengganti pakaian yang tidak layak"
        OCCASION = "occasion", "Acara tertentu"
        VARIETY = "variety", "Menambah variasi koleksi"

    class Decision(models.TextChoices):
        UNDECIDED = "undecided", "Belum diputuskan"
        USE_EXISTING = "use_existing", "Pakai pakaian yang ada"
        REPAIR = "repair", "Perbaiki pakaian yang ada"
        BORROW_RENT = "borrow_rent", "Pinjam atau sewa"
        ALTERNATIVE = "alternative", "Cari alternatif"
        POSTPONE = "postpone", "Tunda pembelian"
        BUY = "buy", "Beli dengan rencana pemakaian"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="purchase_analyses",
    )
    clothing_name = models.CharField("Nama pakaian", max_length=150)
    category = models.CharField("Kategori", max_length=20, choices=Category.choices)
    brand = models.CharField("Merek", max_length=100, blank=True)
    product_url = models.URLField(
        "Link pembelian", max_length=500, blank=True,
        validators=[URLValidator(schemes=["http", "https"])],
    )
    existing_clothing = models.CharField(
        "Pakaian yang sudah dimiliki", max_length=20,
        choices=ExistingClothing.choices,
    )
    purpose = models.CharField(
        "Tujuan penggunaan", max_length=20, choices=Purpose.choices,
    )
    price = models.DecimalField(
        "Harga pakaian (Rp)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    budget = models.DecimalField(
        "Budget pembelian (Rp)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    expected_wears = models.PositiveIntegerField(
        "Perkiraan total pemakaian", validators=[MinValueValidator(1)],
    )
    target_cpw = models.DecimalField(
        "Target biaya per pakai (Rp)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    wears_per_month = models.DecimalField(
        "Pemakaian per bulan", max_digits=6, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    decision = models.CharField(
        "Keputusan", max_length=20, choices=Decision.choices,
        default=Decision.UNDECIDED,
    )
    decision_note = models.TextField("Catatan keputusan", max_length=1000, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    # Snapshot tepercaya dari modul karbon, bukan input dari pengguna.
    carbon_kg_co2e = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    carbon_reference = models.CharField(max_length=200, blank=True)
    carbon_source = models.CharField(max_length=200, blank=True)
    carbon_scope = models.CharField(max_length=500, blank=True)
    carbon_estimated_at = models.DateTimeField(null=True, blank=True)
    rule_version = models.PositiveSmallIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.clothing_name