from decimal import Decimal

import requests
from django.conf import settings

from .constants import (
    FALLBACK_DEFAULT_KG_CO2E_PER_KG,
    FALLBACK_KG_CO2E_PER_KG,
    MONEY_FACTOR_ID,
    PRICE_CURRENCY,
    SCORE_MAX_CO2E_PER_WEAR,
)

BASE_URL = "https://api.climatiq.io/data/v1"
SOURCE_CLIMATIQ = "climatiq"
SOURCE_FALLBACK = "fallback"


class ClimatiqError(Exception):
    """Dilempar kalau panggilan ke Climatiq gagal atau responsnya tidak sesuai harapan."""


def _headers():
    return {"Authorization": f"Bearer {getattr(settings, 'CLIMATIQ_API_KEY', '')}"}


def search_factors(query, results_per_page=10):
    """Cari emission factor berbasis berat. Dipakai untuk eksplorasi, bukan per request user."""
    try:
        resp = requests.get(
            f"{BASE_URL}/search",
            headers=_headers(),
            params={
                "query": query,
                "data_version": settings.CLIMATIQ_DATA_VERSION,
                "unit_type": "Weight",
                "results_per_page": results_per_page,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["results"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise ClimatiqError(str(exc)) from exc


def estimate_money_co2e(factor_id, amount, currency):
    """Panggil /estimate dengan faktor berbasis uang dan kembalikan kg CO2e."""
    payload = {
        "emission_factor": {"id": factor_id},
        "parameters": {"money": float(amount), "money_unit": currency},
    }
    try:
        resp = requests.post(f"{BASE_URL}/estimate", headers=_headers(), json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        co2e, unit = data["co2e"], data["co2e_unit"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise ClimatiqError(str(exc)) from exc
    if unit != "kg":
        raise ClimatiqError(f"Unit tak terduga dari Climatiq: {unit}")
    if co2e <= 0:
        raise ClimatiqError(f"Nilai emisi tidak wajar: {co2e}")
    return float(co2e)


def _to_decimal(value):
    return Decimal(str(round(value, 2)))


def compute_co2e(material, weight_kg, price=None):
    """Kembalikan (kg CO2e sebagai Decimal, sumber data).

    Kalau harga diisi dan API key tersedia, hitung lewat Climatiq (faktor
    Indonesia berbasis uang). Selain itu, atau kalau panggilan gagal, pakai
    berat dikali tabel cadangan per material supaya aplikasi tetap jalan.
    """
    if price and getattr(settings, "CLIMATIQ_API_KEY", ""):
        try:
            return _to_decimal(estimate_money_co2e(MONEY_FACTOR_ID, price, PRICE_CURRENCY)), SOURCE_CLIMATIQ
        except ClimatiqError:
            pass
    rate = FALLBACK_KG_CO2E_PER_KG.get(material, FALLBACK_DEFAULT_KG_CO2E_PER_KG)
    return _to_decimal(float(weight_kg) * rate), SOURCE_FALLBACK


def sustainability_score(co2e_kg, wears):
    """Skor 0-100: makin kecil emisi per pemakaian, makin tinggi skornya."""
    if not wears:
        return 0
    per_wear = float(co2e_kg) / wears
    return max(0, min(100, round(100 * (1 - per_wear / SCORE_MAX_CO2E_PER_WEAR))))
