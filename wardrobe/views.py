import json

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core import serializers
from .models import ClothingItem
from .forms import ClothingItemForm

# Create your views here.

def show_wardrobe(request):
    context = {
        'form': ClothingItemForm(),
        'username': request.user.username
    }
    return render(request, 'wardrobe.html', context)

@login_required
def get_wardrobe_json(request):
    category_query = request.GET.get('category', '').strip()
    items = ClothingItem.objects.filter(user=request.user)
    if category_query:
        items = items.filter(category=category_query)

    data = []
    for item in items:
        data.append({
            "pk": str(item.id),
            "fields": {
                "name": item.name,
                "category": item.get_category_display(),
                "category_code": item.category,
                "material": item.material,
                "price": str(item.price),
                "purchase_data": str(item.purchase_date),
                "image_url": item.image_url or '',
                "wear_count": item.wear_count,
                "cost_per_wear": item.calculate_cost_per_wear(),
            }
        })
    return JsonResponse(data, safe=False)

@login_required
@require_POST
def add_clothing_ajax(request):
    form = ClothingItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        return JsonResponse({"message": "Pakaian berhasil ditambahkan!", "pk": str(item.id)}, status=201)
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

@login_required
@require_POST
def increment_wear_ajax(request, item_id):
    item = get_object_or_404(ClothingItemForm, id=item_id, user=request.user)
    item.wear_count += 1
    item.save()
    return JsonResponse({
        "message": "Jumlah pemakaian diperbarui!",
        "new_wear_count": item_wear_count,
        "new_cpw": item.calculate_cost_per_wear(),
    })

@login_required
@require_POST
def delete_clothing_ajax(request, item_id):
    item = get_object_or_404(ClothingItem, id=item_id, user=request.user)
    item.delete()
    return JsonResponse({"message": "Pakaian berhasil dihapus!"}, status=200)
