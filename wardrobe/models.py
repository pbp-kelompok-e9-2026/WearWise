import uuid

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class ClothingItem(models.Model):
    CATEGORY_CHOICES = [
        ('TOP', 'Atasan / Tops'),
        ('BOTTOM', 'Bawahan / Bottoms'),
        ('OUTER', 'Pakaian Luar / Outerwear'),
        ('DRESS', 'Gaun / Dress'),
        ('SHOES', 'Sepatu / Shoes'),
        ('ACCESSORY', 'Aksesoris / Accessories'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wardrobe_items')
    name = models.CharField(max_length=2555)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    material = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateField()
    image_url = models.URLField(max_length=500, blank=True, null=True)
    wear_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_cost_per_wear(self):
        if self.wear_count == 0:
            return float(self.price)
        return round(float(self.price) / self.wear_count, 2)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

