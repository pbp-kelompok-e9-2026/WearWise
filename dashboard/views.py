from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render, redirect
from django.contrib.auth import login
from dashboard.forms import RegisterForm

from dashboard.models import Profile
from wardrobe.models import ClothingItem

# Target pemakaian per pakaian yang dianggap "100% berkelanjutan".
TARGET_WEARS_PER_ITEM = 30


@login_required
def show_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    totals = ClothingItem.objects.filter(user=request.user).aggregate(
        item_count=Count('id'),
        total_wears=Sum('wear_count'),
        total_spent=Sum('price'),
    )
    item_count = totals['item_count'] or 0
    wears = totals['total_wears'] or 0
    spent = float(totals['total_spent'] or 0)

    # Rata-rata cost per wear seluruh wardrobe
    avg_cost_per_wear = round(spent / wears) if wears else 0

    # Skor keberlanjutan: seberapa sering rata-rata pakaian dipakai vs target
    if item_count:
        score = min(100, round(wears / item_count / TARGET_WEARS_PER_ITEM * 100))
    else:
        score = 0

    context = {
        'profile': profile,
        'wears_logged': wears,
        'avg_cost_per_wear': avg_cost_per_wear,
        'sustainability_score': score,
    }
    return render(request, 'profile.html', context)

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)   # langsung login setelah daftar
            return redirect('dashboard:show_profile')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})