from django import forms
from django.utils.html import strip_tags
from .models import ClothingItem

class ClothingItemForm(forms.ModelForm):
    class Meta:
        model = ClothingItem
        fields = ['name', 'category', 'material', 
                  'price', 'purchase_date', 'image_url', 
                  'wear_count',
                ]

    def clean_name(self):
        name = self.cleaned_data.get("name")
        return strip_tags(name)

    def clean_material(self):
        material = self.cleaned_data.get("material")
        return strip_tags(material)
    