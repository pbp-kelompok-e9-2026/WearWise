from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ConditionRecordForm
from .models import ConditionRecord
from .services import REPAIR_GUIDES, recommend


def _user_records(request):
    records = ConditionRecord.objects.filter(user=request.user).select_related("item")

    recommendation = request.GET.get("recommendation")
    status = request.GET.get("status")
    if recommendation:
        records = records.filter(recommendation=recommendation)
    if status:
        records = records.filter(status=status)
    return records


@login_required
def record_list(request):
    context = {
        "records": _user_records(request),
        "recommendation_choices": ConditionRecord.Recommendation.choices,
        "status_choices": ConditionRecord.Status.choices,
        "selected_recommendation": request.GET.get("recommendation", ""),
        "selected_status": request.GET.get("status", ""),
        "form": ConditionRecordForm(user=request.user),
        "guides": REPAIR_GUIDES,
    }
    return render(request, "lifecycle/list.html", context)


@login_required
def record_create(request):
    form = ConditionRecordForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.user = request.user
        record.recommendation = recommend(record.condition)
        record.save()
        messages.success(request, "Catatan kondisi berhasil ditambahkan.")
        return redirect("lifecycle:index")
    return render(request, "lifecycle/form.html", {"form": form, "title": "Catat kondisi pakaian"})


@login_required
def record_update(request, pk):
    record = get_object_or_404(ConditionRecord, pk=pk, user=request.user)
    form = ConditionRecordForm(request.POST or None, instance=record, user=request.user)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.recommendation = recommend(record.condition)
        record.save()
        messages.success(request, "Catatan kondisi berhasil diperbarui.")
        return redirect("lifecycle:index")
    return render(request, "lifecycle/form.html", {"form": form, "title": "Ubah catatan kondisi"})


@login_required
def record_delete(request, pk):
    record = get_object_or_404(ConditionRecord, pk=pk, user=request.user)
    if request.method == "POST":
        record.delete()
        messages.success(request, "Catatan kondisi berhasil dihapus.")
        return redirect("lifecycle:index")
    return render(request, "lifecycle/confirm_delete.html", {"record": record})


def _serialize(record):
    return {
        "id": str(record.id),
        "item": record.item.name,
        "condition": record.condition,
        "condition_display": record.get_condition_display(),
        "damage_description": record.damage_description,
        "recommendation": record.recommendation,
        "recommendation_display": record.get_recommendation_display(),
        "status": record.status,
        "status_display": record.get_status_display(),
        "created_at": record.created_at.isoformat(),
    }


@login_required
def record_list_json(request):
    data = [_serialize(record) for record in _user_records(request)]
    return JsonResponse({"records": data})


@login_required
@require_POST
def record_create_ajax(request):
    form = ConditionRecordForm(request.POST, user=request.user)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    record = form.save(commit=False)
    record.user = request.user
    record.recommendation = recommend(record.condition)
    record.save()
    return JsonResponse({"record": _serialize(record)}, status=201)


@login_required
@require_POST
def record_status_ajax(request, pk):
    record = get_object_or_404(ConditionRecord, pk=pk, user=request.user)
    status = request.POST.get("status")
    if status not in ConditionRecord.Status.values:
        return JsonResponse({"error": "Status tidak valid."}, status=400)
    record.status = status
    record.save(update_fields=["status", "updated_at"])
    return JsonResponse({"record": _serialize(record)})


@login_required
@require_POST
def record_delete_ajax(request, pk):
    record = get_object_or_404(ConditionRecord, pk=pk, user=request.user)
    record.delete()
    return JsonResponse({"deleted": str(pk)})