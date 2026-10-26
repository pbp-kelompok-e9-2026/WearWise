"""Transparent purchase rules and an adapter to the group's carbon module.

Scores are application heuristics, not scientific sustainability ratings.
See INTEGRATION.md for the rule weights and frontend contract.
"""

from dataclasses import dataclass
from decimal import Decimal, DecimalException, ROUND_CEILING, ROUND_HALF_UP

from django.utils import timezone
from requests import RequestException

from carbon_footprint.constants import (
    FALLBACK_DEFAULT_KG_CO2E_PER_KG, FALLBACK_KG_CO2E_PER_KG, MONEY_FACTOR_ID,
)
from carbon_footprint.services import (
    ClimatiqError, SOURCE_CLIMATIQ, SOURCE_FALLBACK, compute_co2e,
)

from .models import PurchaseAnalysis

RULE_VERSION = 1
CENT = Decimal("0.01")


@dataclass(frozen=True)
class AnalysisResult:
    cost_per_wear: Decimal
    purchase_score: int
    score_breakdown: dict
    within_budget: bool
    meets_cpw_target: bool
    wears_to_target: int
    months_to_target: int | None
    recommendation: str
    recommendation_label: str
    reason: str
    rule_version: int
    carbon_per_wear: Decimal | None


def analyze(item):
    """Calculate from validated inputs; comparison uses unrounded amounts."""
    if item.price <= 0 or item.expected_wears < 1 or item.target_cpw <= 0 or item.budget < 0:
        raise ValueError("Input harga, budget, pemakaian, atau target tidak valid.")
    cpw = item.price / item.expected_wears
    within_budget = item.price <= item.budget
    meets_target = cpw <= item.target_cpw
    breakdown = {
        "cost_per_wear": Decimal(40) * min(Decimal(1), item.target_cpw / cpw),
        "budget": Decimal(30) * min(Decimal(1), item.budget / item.price),
        "existing_clothing": Decimal({"none": 20, "repairable": 10, "usable": 0}[item.existing_clothing]),
        "purpose": Decimal({"routine": 10, "replacement": 10, "occasion": 5, "variety": 0}[item.purpose]),
    }
    score = int(sum(breakdown.values()).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    wears_to_target = int((item.price / item.target_cpw).to_integral_value(rounding=ROUND_CEILING))
    months = None
    if item.wears_per_month is not None and item.wears_per_month > 0:
        months = int((Decimal(wears_to_target) / item.wears_per_month).to_integral_value(rounding=ROUND_CEILING))

    decision = PurchaseAnalysis.Decision
    if item.existing_clothing == PurchaseAnalysis.ExistingClothing.USABLE:
        recommendation, reason = decision.USE_EXISTING, "Kamu masih memiliki pakaian serupa yang layak dipakai."
    elif item.existing_clothing == PurchaseAnalysis.ExistingClothing.REPAIRABLE:
        recommendation, reason = decision.REPAIR, "Pertimbangkan memperbaiki pakaian serupa yang sudah dimiliki."
    elif not within_budget:
        recommendation, reason = decision.POSTPONE, "Harga pakaian melebihi budget pembelianmu."
    elif item.purpose == PurchaseAnalysis.Purpose.OCCASION:
        recommendation, reason = decision.BORROW_RENT, "Untuk acara tertentu, pertimbangkan meminjam atau menyewa."
    elif not meets_target:
        recommendation, reason = decision.ALTERNATIVE, "Biaya per pakai masih di atas target yang kamu tentukan."
    elif item.purpose == PurchaseAnalysis.Purpose.VARIETY:
        recommendation, reason = decision.POSTPONE, "Beri jeda sebelum membeli untuk menambah variasi koleksi."
    else:
        recommendation, reason = decision.BUY, "Sesuai budget dan target biaya per pakai untuk kebutuhanmu."

    carbon_per_wear = None
    if item.carbon_kg_co2e is not None:
        carbon_per_wear = (item.carbon_kg_co2e / item.expected_wears).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return AnalysisResult(
        cost_per_wear=cpw.quantize(CENT, rounding=ROUND_HALF_UP),
        purchase_score=score,
        score_breakdown={key: value.quantize(CENT, rounding=ROUND_HALF_UP) for key, value in breakdown.items()},
        within_budget=within_budget,
        meets_cpw_target=meets_target,
        wears_to_target=wears_to_target,
        months_to_target=months,
        recommendation=recommendation.value,
        recommendation_label=recommendation.label,
        reason=reason,
        rule_version=RULE_VERSION,
        carbon_per_wear=carbon_per_wear,
    )


def refresh_carbon_snapshot(item):
    """Use Zidan's service; return a notice on failure without blocking the CRUD.

    Missing/failed carbon data is None (not zero). Never reuse an old snapshot
    after changing its inputs. This function does not save the database row.
    """
    item.carbon_kg_co2e = None
    item.carbon_reference = ""
    item.carbon_source = ""
    item.carbon_scope = ""
    item.carbon_estimated_at = None
    if not item.material or item.weight_kg is None:
        return ""
    try:
        amount, source = compute_co2e(item.material, item.weight_kg, item.price)
        amount = Decimal(str(amount))
        if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.9999"):
            raise ValueError("Nilai karbon tidak valid.")
        amount = amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if amount <= 0 or source not in (SOURCE_CLIMATIQ, SOURCE_FALLBACK):
            raise ValueError("Sumber atau presisi karbon tidak valid.")
    except (ClimatiqError, RequestException, DecimalException, ValueError, TypeError, OverflowError):
        return "Analisis tersimpan, tetapi estimasi karbon belum tersedia. Coba perbarui estimasi karbon nanti."

    item.carbon_kg_co2e = amount
    item.carbon_source = source
    if source == SOURCE_CLIMATIQ:
        item.carbon_reference = f"Climatiq / CEDA 2025 / {MONEY_FACTOR_ID}"
        item.carbon_scope = "Estimasi produksi pakaian Indonesia berbasis harga (IDR); material tidak memengaruhi faktor berbasis uang ini. Bukan keseluruhan siklus hidup."
    else:
        factor = FALLBACK_KG_CO2E_PER_KG.get(item.material, FALLBACK_DEFAULT_KG_CO2E_PER_KG)
        item.carbon_reference = f"Tabel cadangan modul karbon / {item.material} / {factor} kg CO2e per kg"
        item.carbon_scope = "Estimasi kasar berdasarkan berat dan faktor material dari modul karbon; bukan respons API Climatiq atau keseluruhan siklus hidup."
    item.carbon_estimated_at = timezone.now()
    return ""
