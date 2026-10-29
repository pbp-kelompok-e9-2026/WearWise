"""Agregasi untuk ruang Analyzer: membaca estimasi SEMUA user, tetapi hanya menampilkan angka gabungan.

Nama user dan nama item sengaja tidak ikut ke hasil. Akun Analyzer tidak boleh membaca data pribadi user,
sama seperti aturan di modul Worth to Buy.
"""
from .constants import CATEGORY_CHOICES, MATERIAL_CHOICES
from .models import CarbonEstimate
from .services import SOURCE_CLIMATIQ, sustainability_score

TOP_N = 10
SCORE_LOW = 40     # skor di bawah ini dianggap rendah
SCORE_HIGH = 70    # skor dari sini ke atas dianggap tinggi


def _pct(part, whole):
    return round(part / whole * 100) if whole else 0


def _group(rows, key, choices):
    """Rata-rata emisi total dan per pemakaian untuk tiap nilai `key` (material atau kategori)."""
    labels = dict(choices)
    buckets = {}
    for row in rows:
        buckets.setdefault(row[key], []).append(row)
    out = []
    for value, items in buckets.items():
        out.append({
            "label": labels.get(value, value),
            "count": len(items),
            "avg_co2e": sum(r["co2e"] for r in items) / len(items),
            "avg_per_wear": sum(r["per_wear"] for r in items) / len(items),
        })
    out.sort(key=lambda g: g["avg_co2e"], reverse=True)
    peak = max((g["avg_co2e"] for g in out), default=0)
    for g in out:
        g["bar_pct"] = _pct(g["avg_co2e"], peak)
    return out


def build_analysis():
    raw = CarbonEstimate.objects.values(
        "user_id", "material", "category", "co2e_kg", "estimated_wears", "source"
    )
    rows = []
    for r in raw:
        co2e = float(r["co2e_kg"])
        wears = r["estimated_wears"] or 1
        rows.append({
            "user": r["user_id"],
            "material": r["material"],
            "category": r["category"],
            "source": r["source"],
            "co2e": co2e,
            "per_wear": co2e / wears,
            "score": sustainability_score(co2e, wears),
        })

    total = len(rows)
    climatiq = sum(1 for r in rows if r["source"] == SOURCE_CLIMATIQ)
    material_labels = dict(MATERIAL_CHOICES)
    category_labels = dict(CATEGORY_CHOICES)
    # Hanya kombinasi kategori + material, tanpa nama item dan tanpa pemiliknya.
    top = [
        {
            "category_label": category_labels.get(r["category"], r["category"]),
            "material_label": material_labels.get(r["material"], r["material"]),
            "source": r["source"],
            "co2e": r["co2e"],
            "per_wear": r["per_wear"],
            "score": r["score"],
        }
        for r in sorted(rows, key=lambda r: r["per_wear"], reverse=True)[:TOP_N]
    ]

    return {
        "total": total,
        "users": len({r["user"] for r in rows}),
        "avg_co2e": sum(r["co2e"] for r in rows) / total if total else 0,
        "avg_score": round(sum(r["score"] for r in rows) / total) if total else 0,
        "climatiq_pct": _pct(climatiq, total),
        "fallback_pct": 100 - _pct(climatiq, total) if total else 0,
        "score_low": sum(1 for r in rows if r["score"] < SCORE_LOW),
        "score_mid": sum(1 for r in rows if SCORE_LOW <= r["score"] < SCORE_HIGH),
        "score_high": sum(1 for r in rows if r["score"] >= SCORE_HIGH),
        "by_material": _group(rows, "material", MATERIAL_CHOICES),
        "by_category": _group(rows, "category", CATEGORY_CHOICES),
        "top": top,
    }
