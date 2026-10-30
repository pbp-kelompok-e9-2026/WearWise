"""Data awal: 50 referensi pakaian untuk katalog Worth to Buy.

Data ini sintetis (contoh), bukan harga resmi dari toko mana pun.
Migration dilewati saat `manage.py test` supaya test modul lain tidak berubah.
"""
import sys
from decimal import Decimal

from django.db import migrations

SOURCE = "Data sintetis WiseFit (contoh untuk data awal)"

# (nama, kategori, bahan, harga Rp, berat kg)
REFERENCES = [
    ("Kaos katun basic putih", "top", "cotton", 79000, "0.20"),
    ("Kaos katun basic hitam", "top", "cotton", 79000, "0.20"),
    ("Kaos oversized abu-abu", "top", "cotton", 99000, "0.25"),
    ("Kaos polo katun navy", "top", "cotton", 149000, "0.25"),
    ("Kemeja katun putih lengan panjang", "top", "cotton", 199000, "0.25"),
    ("Kemeja flanel kotak-kotak", "top", "cotton", 229000, "0.35"),
    ("Kemeja oxford biru muda", "top", "cotton", 249000, "0.28"),
    ("Blus katun motif bunga", "top", "cotton", 179000, "0.20"),
    ("Kaos olahraga dry-fit", "top", "polyester", 89000, "0.15"),
    ("Kemeja polyester anti kusut", "top", "polyester", 169000, "0.22"),
    ("Blus satin polyester", "top", "polyester", 189000, "0.18"),
    ("Kemeja sutra krem", "top", "silk", 599000, "0.15"),
    ("Blus sutra lengan pendek", "top", "silk", 549000, "0.14"),
    ("Sweater rajut wol abu-abu", "top", "wool", 399000, "0.45"),
    ("Cardigan wol cokelat", "top", "wool", 449000, "0.40"),
    ("Sweater crewneck katun", "top", "cotton", 259000, "0.45"),
    ("Hoodie katun fleece", "top", "cotton", 299000, "0.55"),
    ("Celana jeans slim fit", "bottom", "cotton", 349000, "0.60"),
    ("Celana jeans straight biru tua", "bottom", "cotton", 379000, "0.65"),
    ("Celana chino krem", "bottom", "cotton", 249000, "0.45"),
    ("Celana chino hitam", "bottom", "cotton", 249000, "0.45"),
    ("Celana kulot katun", "bottom", "cotton", 199000, "0.40"),
    ("Celana pendek katun", "bottom", "cotton", 129000, "0.25"),
    ("Celana jogger polyester", "bottom", "polyester", 179000, "0.35"),
    ("Celana bahan kerja", "bottom", "polyester", 229000, "0.40"),
    ("Rok plisket polyester", "bottom", "polyester", 159000, "0.30"),
    ("Rok denim A-line", "bottom", "cotton", 219000, "0.40"),
    ("Celana wol formal", "bottom", "wool", 499000, "0.50"),
    ("Jaket denim klasik", "outer", "cotton", 449000, "0.80"),
    ("Jaket parka katun", "outer", "cotton", 549000, "0.90"),
    ("Jaket windbreaker", "outer", "polyester", 299000, "0.35"),
    ("Jaket puffer ringan", "outer", "polyester", 499000, "0.50"),
    ("Jaket bomber polyester", "outer", "polyester", 399000, "0.60"),
    ("Blazer polyester hitam", "outer", "polyester", 459000, "0.70"),
    ("Mantel wol panjang", "outer", "wool", 899000, "1.20"),
    ("Blazer wol abu-abu", "outer", "wool", 799000, "0.85"),
    ("Kemeja overshirt katun", "outer", "cotton", 279000, "0.50"),
    ("Dress katun midi", "dress", "cotton", 279000, "0.35"),
    ("Dress kemeja katun", "dress", "cotton", 299000, "0.35"),
    ("Dress polyester motif", "dress", "polyester", 229000, "0.30"),
    ("Dress satin pesta", "dress", "polyester", 399000, "0.35"),
    ("Dress sutra slip", "dress", "silk", 749000, "0.20"),
    ("Gamis katun polos", "dress", "cotton", 329000, "0.50"),
    ("Dress rajut wol", "dress", "wool", 549000, "0.55"),
    ("Jumpsuit katun", "dress", "cotton", 319000, "0.45"),
    ("Syal wol", "other", "wool", 149000, "0.15"),
    ("Syal sutra", "other", "silk", 249000, "0.08"),
    ("Kaos kaki katun (3 pasang)", "other", "cotton", 59000, "0.10"),
    ("Topi bucket katun", "other", "cotton", 89000, "0.10"),
    ("Pashmina polyester", "other", "polyester", 79000, "0.12"),
]


def add_references(apps, schema_editor):
    if "test" in sys.argv:
        return
    ClothingReference = apps.get_model("worth_to_buy_analyzer", "ClothingReference")
    for name, category, material, price, weight in REFERENCES:
        ClothingReference.objects.get_or_create(
            clothing_name=name,
            source_name=SOURCE,
            defaults={
                "category": category,
                "material": material,
                "price": Decimal(price),
                "weight_kg": Decimal(weight),
                "notes": "Harga dan berat adalah perkiraan untuk data contoh.",
                "is_published": True,
            },
        )


def remove_references(apps, schema_editor):
    ClothingReference = apps.get_model("worth_to_buy_analyzer", "ClothingReference")
    ClothingReference.objects.filter(source_name=SOURCE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("worth_to_buy_analyzer", "0005_analyzer_role"),
    ]

    operations = [
        migrations.RunPython(add_references, remove_references),
    ]
