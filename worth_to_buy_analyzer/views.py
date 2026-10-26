from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import DecisionForm, PurchaseAnalysisForm
from .models import PurchaseAnalysis
from .services import RULE_VERSION, analyze, refresh_carbon_snapshot


def _owned_analysis(request, pk):
    return get_object_or_404(PurchaseAnalysis, pk=pk, owner=request.user)


@login_required
@require_GET
def analyzer(request):
    items = PurchaseAnalysis.objects.filter(owner=request.user).order_by("-created_at", "-pk")
    page = Paginator(items, 10).get_page(request.GET.get("page"))
    return render(request, "worth_to_buy_analyzer/analyzer.html", {"page_obj": page})


def _save_form(request, item=None):
    item = item or PurchaseAnalysis(owner=request.user)
    form = PurchaseAnalysisForm(request.POST if request.method == "POST" else None, instance=item)
    if request.method == "POST" and form.is_valid():
        is_new = item.pk is None
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.rule_version = RULE_VERSION
        if is_new or {"material", "weight_kg", "price"} & set(form.changed_data):
            notice = refresh_carbon_snapshot(obj)
            if notice:
                messages.warning(request, notice)
        # A decision made on old inputs must be reconsidered after editing.
        if not is_new and form.changed_data:
            obj.decision = PurchaseAnalysis.Decision.UNDECIDED
            obj.decided_at = None
        obj.save()
        messages.success(request, "Analisis berhasil disimpan.")
        return redirect("worth_to_buy_analyzer:detail", pk=obj.pk)
    return render(request, "worth_to_buy_analyzer/form.html", {
        "form": form, "item": item, "mode": "update" if item.pk else "create",
    })


@login_required
@require_http_methods(["GET", "POST"])
def create(request):
    return _save_form(request)


@login_required
@require_GET
def detail(request, pk):
    item = _owned_analysis(request, pk)
    return render(request, "worth_to_buy_analyzer/detail.html", {
        "item": item, "result": analyze(item), "decision_form": DecisionForm(instance=item),
    })


@login_required
@require_http_methods(["GET", "POST"])
def update(request, pk):
    return _save_form(request, _owned_analysis(request, pk))


@login_required
@require_http_methods(["GET", "POST"])
def delete(request, pk):
    item = _owned_analysis(request, pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Analisis berhasil dihapus.")
        return redirect("worth_to_buy_analyzer:analyzer")
    return render(request, "worth_to_buy_analyzer/confirm_delete.html", {"item": item})


@login_required
@require_POST
def decide(request, pk):
    item = _owned_analysis(request, pk)
    previous_decision = item.decision
    form = DecisionForm(request.POST, instance=item)
    if form.is_valid():
        obj = form.save(commit=False)
        if obj.decision == PurchaseAnalysis.Decision.UNDECIDED:
            obj.decided_at = None
        elif obj.decision != previous_decision or obj.decided_at is None:
            obj.decided_at = timezone.now()
        obj.save(update_fields=["decision", "decision_note", "decided_at", "updated_at"])
        messages.success(request, "Keputusan berhasil disimpan.")
        return redirect("worth_to_buy_analyzer:detail", pk=obj.pk)
    return render(request, "worth_to_buy_analyzer/detail.html", {
        "item": item, "result": analyze(item), "decision_form": form,
    })


@login_required
@require_POST
def refresh_carbon(request, pk):
    item = _owned_analysis(request, pk)
    notice = refresh_carbon_snapshot(item)
    item.save(update_fields=[
        "carbon_kg_co2e", "carbon_reference", "carbon_source", "carbon_scope",
        "carbon_estimated_at", "updated_at",
    ])
    if notice:
        messages.warning(request, notice)
    elif item.carbon_kg_co2e is None:
        messages.info(request, "Lengkapi material dan berat pakaian untuk menyertakan estimasi karbon.")
    else:
        messages.success(request, "Estimasi karbon berhasil diperbarui.")
    return redirect("worth_to_buy_analyzer:detail", pk=item.pk)
