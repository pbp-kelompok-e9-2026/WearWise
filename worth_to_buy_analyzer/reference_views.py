"""Analyzer workspace and the published catalogue consumed by ordinary users."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ClothingReferenceForm
from .models import ClothingReference, PurchaseAnalysis
from .roles import analyzer_required, purchase_user_required


def _search(request, items):
    query = request.GET.get("q", "").strip()[:100]
    category = request.GET.get("category", "")
    if query:
        items = items.filter(
            Q(clothing_name__icontains=query) | Q(brand__icontains=query) | Q(source_name__icontains=query)
        )
    if category in PurchaseAnalysis.Category.values:
        items = items.filter(category=category)
    else:
        category = ""
    params = request.GET.copy()
    params.pop("page", None)
    return {
        "page_obj": Paginator(items, 12).get_page(request.GET.get("page")),
        "query": query, "category": category, "categories": PurchaseAnalysis.Category.choices,
        "filter_query": params.urlencode(),
    }


@analyzer_required
@require_GET
def reference_list(request):
    items = ClothingReference.objects.select_related("updated_by")
    status = request.GET.get("status", "")
    if status in ("published", "draft"):
        items = items.filter(is_published=status == "published")
    context = _search(request, items)
    context.update({
        "status": status,
        "total_count": ClothingReference.objects.count(),
        "published_count": ClothingReference.objects.filter(is_published=True).count(),
        "draft_count": ClothingReference.objects.filter(is_published=False).count(),
    })
    return render(request, "worth_to_buy_analyzer/references/list.html", context)


def _reference_form(request, item=None):
    form = ClothingReferenceForm(request.POST if request.method == "POST" else None, instance=item)
    if request.method == "POST" and form.is_valid():
        reference = form.save(commit=False)
        if reference.pk is None:
            reference.created_by = request.user
        reference.updated_by = request.user
        reference.save()
        messages.success(request, "Referensi pakaian berhasil disimpan.")
        return redirect("worth_to_buy_analyzer:reference_detail", pk=reference.pk)
    return render(request, "worth_to_buy_analyzer/references/form.html", {"form": form, "item": item})


@analyzer_required
@require_http_methods(["GET", "POST"])
def reference_create(request):
    return _reference_form(request)


@analyzer_required
@require_GET
def reference_detail(request, pk):
    item = get_object_or_404(ClothingReference.objects.select_related("created_by", "updated_by"), pk=pk)
    return render(request, "worth_to_buy_analyzer/references/detail.html", {"item": item})


@analyzer_required
@require_http_methods(["GET", "POST"])
def reference_update(request, pk):
    return _reference_form(request, get_object_or_404(ClothingReference, pk=pk))


@analyzer_required
@require_http_methods(["GET", "POST"])
def reference_delete(request, pk):
    item = get_object_or_404(ClothingReference, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Referensi pakaian berhasil dihapus. Analisis user yang sudah disimpan tetap utuh.")
        return redirect("worth_to_buy_analyzer:reference_list")
    return render(request, "worth_to_buy_analyzer/references/confirm_delete.html", {"item": item})


@purchase_user_required
@require_GET
def catalogue(request):
    context = _search(request, ClothingReference.objects.filter(is_published=True))
    return render(request, "worth_to_buy_analyzer/catalogue.html", context)
