from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .constants import PRICE_CURRENCY_LABEL
from .forms import CarbonEstimateForm
from .models import CarbonEstimate

# Skala untuk elemen visual di halaman "Numbers" (mengikuti desain Figma).
WEAR_DOTS = 24      # jumlah titik pada baris Estimated Wears
WEAR_TARGET = 32    # jumlah wears yang dianggap "penuh" untuk titik
COST_MAX = 200_000  # cost per wear (Rupiah) yang memenuhi batang (sekitar $12, seperti di desain)
CARBON_MAX = 10     # kg CO2e yang memenuhi batang


def _pct(value, maximum):
    """Ubah nilai menjadi persen bulat 0-100 (bulat supaya aman dari format desimal locale)."""
    return max(0, min(100, round(value / maximum * 100)))


def build_stats(wears, cost_per_wear, carbon_kg, score):
    """Siapkan semua angka yang dibutuhkan template Numbers."""
    filled = round(WEAR_DOTS * min(wears / WEAR_TARGET, 1))
    return {
        "wears": wears,
        "dots": [i < filled for i in range(WEAR_DOTS)],
        "cost_per_wear": cost_per_wear,
        "cost_pct": _pct(cost_per_wear, COST_MAX) if cost_per_wear is not None else 0,
        "carbon_kg": carbon_kg,
        "carbon_pct": _pct(carbon_kg, CARBON_MAX),
        "score": score,
        "score_pct": _pct(score, 100),
    }


def _user_estimates(request):
    # Selalu difilter per user, supaya data milik orang lain tidak bisa dibuka lewat URL.
    return CarbonEstimate.objects.filter(user=request.user)


@login_required
def index(request):
    """Read: halaman Numbers untuk satu item (default: yang terbaru, atau ?item=<id>)."""
    estimates = _user_estimates(request)
    item_id = request.GET.get("item", "")
    item = estimates.filter(pk=item_id).first() if item_id.isdigit() else None
    item = item or estimates.first()

    stats = None
    if item:
        stats = build_stats(
            wears=item.estimated_wears,
            cost_per_wear=item.cost_per_wear,
            carbon_kg=float(item.co2e_kg),
            score=item.score,
        )
    context = {"stats": stats, "item": item, "currency": PRICE_CURRENCY_LABEL}
    return render(request, "carbon_footprint/index.html", context)


@login_required
def estimate_list(request):
    """Read: daftar semua estimasi, sekaligus perbandingan emisi antar item."""
    estimates = list(_user_estimates(request))
    peak = max((float(e.co2e_kg) for e in estimates), default=0)
    for e in estimates:
        e.bar_pct = round(float(e.co2e_kg) / peak * 100) if peak else 0
    return render(request, "carbon_footprint/list.html", {"estimates": estimates})


@login_required
def estimate_create(request):
    form = CarbonEstimateForm(request.POST or None, instance=CarbonEstimate(user=request.user))
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{obj.name} added.")
        return redirect("carbon_footprint:list")
    return render(request, "carbon_footprint/form.html", {"form": form, "mode": "create"})


@login_required
def estimate_update(request, pk):
    obj = get_object_or_404(_user_estimates(request), pk=pk)
    form = CarbonEstimateForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{obj.name} updated.")
        return redirect("carbon_footprint:list")
    return render(request, "carbon_footprint/form.html", {"form": form, "mode": "update", "item": obj})


@login_required
def estimate_delete(request, pk):
    obj = get_object_or_404(_user_estimates(request), pk=pk)
    if request.method == "POST":
        name = obj.name
        obj.delete()
        messages.success(request, f"{name} removed.")
        return redirect("carbon_footprint:list")
    return render(request, "carbon_footprint/confirm_delete.html", {"item": obj})
