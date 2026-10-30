import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_headers

from .access import analyzer_required, can_open_analyzer, user_pages_only
from .analysis import SOURCE_CHOICES, build_analysis, clean_filters
from . import services
from .constants import CATEGORY_CHOICES, MATERIAL_CHOICES, PRICE_CURRENCY_LABEL
from .forms import CarbonEstimateForm, FactorsForm, reset_factors
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


# ---------- Bantuan untuk HTMX ----------
# Aturan umum: permintaan HTMX mendapat potongan HTML (parsial) yang mengganti satu bagian halaman,
# sedangkan permintaan biasa (tanpa JavaScript, atau buka lewat URL) tetap mendapat halaman penuh.

SORTS = {
    "newest": ("-updated_at", "-pk"),
    "co2e_desc": ("-co2e_kg",),
    "co2e_asc": ("co2e_kg",),
    "name": ("name",),
}
SORT_CHOICES = [("newest", "Newest"), ("co2e_desc", "Highest CO\u2082e"), ("co2e_asc", "Lowest CO\u2082e"), ("name", "Name A\u2013Z")]


def is_htmx(request):
    """True untuk permintaan HTMX biasa. Pemulihan riwayat (tombol Back) butuh halaman penuh."""
    return request.headers.get("HX-Request") == "true" and not request.headers.get("HX-History-Restore-Request")


def toast_header(response, message):
    """Minta browser menampilkan notifikasi kecil (ditangani static/carbon_footprint/js/cf.js)."""
    response["HX-Trigger"] = json.dumps({"cf:toast": {"message": message}})
    return response


def _filtered_rows(request, params):
    """Daftar estimasi milik user setelah dicari, difilter, dan diurutkan, beserta panjang batangnya."""
    qs = _user_estimates(request)
    q = params.get("q", "").strip()
    material = params.get("material", "")
    sort = params.get("sort", "newest")
    if q:
        qs = qs.filter(name__icontains=q)
    if material in dict(MATERIAL_CHOICES):
        qs = qs.filter(material=material)
    else:
        material = ""
    if sort not in SORTS:
        sort = "newest"
    estimates = list(qs.order_by(*SORTS[sort]))
    peak = max((float(e.co2e_kg) for e in estimates), default=0)
    for e in estimates:
        e.bar_pct = round(float(e.co2e_kg) / peak * 100) if peak else 0
    return {
        "estimates": estimates,
        "filters": {"q": q, "material": material, "sort": sort},
        "filtered": bool(q or material),
    }


def _parse_preview(data):
    """Baca isi form untuk pratinjau. Kembalikan None kalau belum cukup atau tidak valid."""
    material, category = data.get("material", ""), data.get("category", "")
    if material not in dict(MATERIAL_CHOICES) or category not in dict(CATEGORY_CHOICES):
        return None
    try:
        raw_weight = (data.get("weight_kg") or "").strip()
        weight = Decimal(raw_weight) if raw_weight else Decimal(str(services.category_weight(category)))
        raw_price = (data.get("price") or "").strip()
        price = Decimal(raw_price) if raw_price else None
        wears = int(data.get("estimated_wears") or 30)
    except (InvalidOperation, ValueError):
        return None
    if not (0 < weight <= 1000) or (price is not None and not (0 <= price <= 10**10)) or not (1 <= wears <= 100000):
        return None
    # Pratinjau selalu offline (tanpa memanggil Climatiq) supaya mengetik tidak menghabiskan kuota API.
    co2e, _source = services.compute_co2e(material, weight, None)
    return {
        "co2e": float(co2e),
        "weight": weight,
        "wears": wears,
        "cost_per_wear": float(price) / wears if price else None,
        "score": services.sustainability_score(co2e, wears),
        "will_use_climatiq": bool(price) and bool(getattr(settings, "CLIMATIQ_API_KEY", "")),
        "currency": PRICE_CURRENCY_LABEL,
    }


@user_pages_only
@vary_on_headers("HX-Request")
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
    context = {
        "stats": stats,
        "item": item,
        "items": list(estimates.values("pk", "name")),   # untuk pemilih item
        "currency": PRICE_CURRENCY_LABEL,
        "is_analyzer": can_open_analyzer(request.user),
    }
    template = "carbon_footprint/_numbers.html" if is_htmx(request) else "carbon_footprint/index.html"
    return render(request, template, context)


@user_pages_only
@vary_on_headers("HX-Request")
def estimate_list(request):
    """Read: daftar estimasi dengan pencarian, filter material, dan urutan."""
    context = _filtered_rows(request, request.GET)
    context.update({
        "is_analyzer": can_open_analyzer(request.user),
        "material_choices": MATERIAL_CHOICES,
        "sort_choices": SORT_CHOICES,
    })
    template = "carbon_footprint/_rows.html" if is_htmx(request) else "carbon_footprint/list.html"
    return render(request, template, context)


@user_pages_only
@require_POST
def estimate_preview(request):
    """Pratinjau hasil saat user mengisi form (dipanggil HTMX, tidak menyimpan apa pun)."""
    return render(request, "carbon_footprint/_preview.html", {"p": _parse_preview(request.POST)})


@user_pages_only
def estimate_create(request):
    form = CarbonEstimateForm(request.POST or None, instance=CarbonEstimate(user=request.user))
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{obj.name} added.")
        return redirect("carbon_footprint:list")
    return render(request, "carbon_footprint/form.html", {"form": form, "mode": "create", "weights": services.current_category_weights()})


@user_pages_only
def estimate_update(request, pk):
    obj = get_object_or_404(_user_estimates(request), pk=pk)
    form = CarbonEstimateForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{obj.name} updated.")
        return redirect("carbon_footprint:list")
    return render(request, "carbon_footprint/form.html", {"form": form, "mode": "update", "item": obj, "weights": services.current_category_weights()})


@user_pages_only
def estimate_delete(request, pk):
    obj = get_object_or_404(_user_estimates(request), pk=pk)
    if request.method == "POST":
        name = obj.name
        obj.delete()
        if is_htmx(request):
            # Kirim ulang daftar (dengan filter yang sedang aktif) dan tampilkan notifikasi.
            context = _filtered_rows(request, request.POST)
            return toast_header(render(request, "carbon_footprint/_rows.html", context), f"{name} removed.")
        messages.success(request, f"{name} removed.")
        return redirect("carbon_footprint:list")
    return render(request, "carbon_footprint/confirm_delete.html", {"item": obj})


# ---------- Peran Analyzer ----------

@analyzer_required
@vary_on_headers("HX-Request")
def analyzer(request):
    """Analisis gabungan seluruh data (tanpa nama user atau nama item), dengan filter bahan, kategori, dan sumber."""
    filters = clean_filters(request.GET)
    context = {
        "a": build_analysis(**filters),
        "filters": filters,
        "filtered": any(filters.values()),
        "material_choices": MATERIAL_CHOICES,
        "category_choices": CATEGORY_CHOICES,
        "source_choices": SOURCE_CHOICES,
    }
    template = "carbon_footprint/_analysis.html" if is_htmx(request) else "carbon_footprint/analyzer.html"
    return render(request, template, context)


def _factors_context(form):
    return {"form": form, "offline_count": CarbonEstimate.objects.filter(source=services.SOURCE_FALLBACK).count()}


@analyzer_required
def factors(request):
    """Atur faktor emisi per material dan berat per kategori yang dipakai perhitungan."""
    htmx = is_htmx(request)

    if request.method == "POST" and "reset" in request.POST:
        reset_factors()
        if htmx:
            response = render(request, "carbon_footprint/_factors_form.html", _factors_context(FactorsForm()))
            return toast_header(response, "Faktor dikembalikan ke nilai bawaan.")
        messages.success(request, "Faktor dikembalikan ke nilai bawaan.")
        return redirect("carbon_footprint:factors")

    form = FactorsForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        updated = form.save(request.user)
        msg = "Faktor berhasil disimpan."
        if form.cleaned_data["recalculate"]:
            msg += f" {updated} estimasi offline dihitung ulang."
        if htmx:
            # Form baru supaya nilai, penanda "diubah", dan jumlah estimasi offline mengikuti database.
            return toast_header(render(request, "carbon_footprint/_factors_form.html", _factors_context(FactorsForm())), msg)
        messages.success(request, msg)
        return redirect("carbon_footprint:factors")
    template = "carbon_footprint/_factors_form.html" if htmx and request.method == "POST" else "carbon_footprint/factors.html"
    return render(request, template, _factors_context(form))
