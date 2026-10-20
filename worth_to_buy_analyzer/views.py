from django.shortcuts import render

from .models import PurchaseAnalysis


def analyzer(request):
    return render(request, 'worth_to_buy_analyzer/analyzer.html', {
        'categories': PurchaseAnalysis.Category.choices,
        'existing_clothing_choices': PurchaseAnalysis.ExistingClothing.choices,
        'purpose_choices': PurchaseAnalysis.Purpose.choices,
    })
