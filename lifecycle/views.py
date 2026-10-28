from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ConditionRecordForm
from .models import ConditionRecord
from .services import recommend


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


@login_required
def record_list_json(request):
    data = [
        {
            "id": str(record.id),
            "item": record.item.name,
            "condition": record.condition,
            "condition_display": record.get_condition_display(),
            "damage_description": record.damage_description,
            "recommendation": record.recommendation,
            "status": record.status,
            "created_at": record.created_at.isoformat(),
        }
        for record in _user_records(request)
    ]
    return JsonResponse({"records": data})