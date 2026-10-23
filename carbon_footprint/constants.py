"""Konstanta modul Carbon Footprint & Sustainability."""

MATERIAL_CHOICES = [
    ("cotton", "Cotton"),
    ("polyester", "Polyester"),
    ("wool", "Wool"),
    ("linen", "Linen"),
    ("nylon", "Nylon"),
    ("viscose", "Viscose"),
]

CATEGORY_CHOICES = [
    ("t-shirt", "T-shirt"),
    ("shirt", "Shirt"),
    ("dress", "Dress"),
    ("sweater", "Sweater"),
    ("jeans", "Jeans"),
    ("jacket", "Jacket"),
]

# Perkiraan berat per kategori (kg), dipakai kalau user tidak mengisi berat.
# Ini asumsi kasar, bukan data resmi.
CATEGORY_WEIGHT_KG = {
    "t-shirt": 0.2,
    "shirt": 0.25,
    "dress": 0.4,
    "sweater": 0.5,
    "jeans": 0.7,
    "jacket": 0.9,
}

# Faktor emisi Climatiq berbasis uang (spend-based) untuk pakaian di Indonesia:
# "Apparel manufacturing (purchaser prices)", CEDA 2025, region ID.
# Dipilih karena data tekstil berbasis berat yang publik tidak tersedia untuk
# pakaian jadi. Konsekuensinya, material tidak memengaruhi hasil ini, hanya harga.
MONEY_FACTOR_ID = "d9192fe3-6369-8ed7-ac2b-1d4caae09b46"
PRICE_CURRENCY = "idr"        # kode mata uang yang dikirim ke Climatiq (dikonversi otomatis)
PRICE_CURRENCY_LABEL = "Rp"   # label yang ditampilkan di halaman

# kg CO2e per kg kain. Dipakai kalau harga tidak diisi atau Climatiq
# tidak bisa dipanggil.
FALLBACK_KG_CO2E_PER_KG = {
    "cotton": 18.12, # CAEP 2022 China Products Carbon Footprint Factors Database
    "polyester": 25.7, # CAEP 2022 China Products Carbon Footprint Factors Database
    "wool": 2.23, # CAEP 2022 China Products Carbon Footprint Factors Database
    "silk": 18.7 # CAEP 2022 China Products Carbon Footprint Factors Database
}
FALLBACK_DEFAULT_KG_CO2E_PER_KG = 16.2

# Skor keberlanjutan 0-100 = 100 * (1 - (kg CO2e per wear) / SCORE_MAX_CO2E_PER_WEAR).
# Ini rumus sederhana buatan modul ini (bukan dari Climatiq)
SCORE_MAX_CO2E_PER_WEAR = 0.75
