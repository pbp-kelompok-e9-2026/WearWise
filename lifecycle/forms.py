from django import forms

from wardrobe.models import ClothingItem

from .models import ConditionRecord


class ConditionRecordForm(forms.ModelForm):
    class Meta:
        model = ConditionRecord
        fields = ["item", "condition", "damage_description", "notes", "status"]
        labels = {
            "item": "Pakaian",
            "condition": "Kondisi",
            "damage_description": "Jenis kerusakan",
            "notes": "Catatan",
            "status": "Status tindak lanjut",
        }
        widgets = {
            "damage_description": forms.TextInput(attrs={"placeholder": "Misal: kancing lepas, sobek di lengan"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["item"].queryset = ClothingItem.objects.filter(user=user)