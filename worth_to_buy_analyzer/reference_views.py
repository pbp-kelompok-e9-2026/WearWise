"""Analyzer workspace and the published catalogue consumed by ordinary users."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import ClothingReferenceForm
from .htmx import is_partial, page_or_fragment
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


def _workspace_context(request):
    items = ClothingReference.objects.select_related("updated_by")
    status = request.GET.get("status", "")
    if status in ("published", "draft"):
        items = items.filter(is_published=status == "published")
    context = _search(request, items)
    context.update({
        "results_target": "#reference-results", "filter_id": "reference-filters",
        "status": status,
        "total_count": ClothingReference.objects.count(),
        "published_count": ClothingReference.objects.filter(is_published=True).count(),
        "draft_count": ClothingReference.objects.filter(is_published=False).count(),
    })
    return context


@analyzer_required
@require_GET
def reference_list(request):
    return page_or_fragment(
        request, "worth_to_buy_analyzer/references/list.html",
        "worth_to_buy_analyzer/references/_results.html", _workspace_context(request),
    )


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


@analyzer_required
@require_POST
def reference_publish(request, pk):
    # An explicit desired state is safe to retry; do not blindly toggle it.
    if request.POST.get("publication") not in ("publish", "withdraw"):
        return HttpResponseBadRequest("Pilih status publikasi yang valid.")
    item = get_object_or_404(ClothingReference, pk=pk)
    item.is_published = request.POST["publication"] == "publish"
    item.updated_by = request.user
    item.save(update_fields=["is_published", "updated_by", "updated_at"])
    notice = "Referensi diterbitkan ke katalog user." if item.is_published else "Referensi ditarik dari katalog user."
    if is_partial(request):
        context = _workspace_context(request)
        context["notice"] = notice
        response = page_or_fragment(request, "worth_to_buy_analyzer/references/list.html", "worth_to_buy_analyzer/references/_results.html", context)
        # Removing the last result on a page can move the list back one page.
        params = request.GET.copy()
        params["page"] = context["page_obj"].number
        response.headers["HX-Replace-Url"] = reverse("worth_to_buy_analyzer:reference_list") + "?" + params.urlencode()
        return response
    messages.success(request, notice)
    return redirect("worth_to_buy_analyzer:reference_list")


@purchase_user_required
@require_GET
def catalogue(request):
    context = _search(request, ClothingReference.objects.filter(is_published=True))
    context.update({"results_target": "#catalogue-results", "filter_id": "catalogue-filters"})
    return page_or_fragment(request, "worth_to_buy_analyzer/catalogue.html", "worth_to_buy_analyzer/partials/catalogue_results.html", context)
