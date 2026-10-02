from django.test import TestCase, Client
from django.contrib.auth.models import User
from wardrobe.models import ClothingItem

# Create your tests here.
class WardrobeTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='alijundi', password='password123')
        self.item = ClothingItem.objects.create(
            user=self.user,
            name='Kaos Polos',
            category='TOP',
            material='Katun',
            price=50000,
            purchase_date='2026-01-01',
            wear_count=2
        )

    def test_cost_per_wear_calculation(self):
        # 50000 / 2 = 25000
        self.assertEqual(self.item.calculate_cost_per_wear(), 25000.0)

    def test_wardrobe_url_protected(self):
        # Harus redirect jika belum login
        response = self.client.get('/wardrobe/')
        self.assertEqual(response.status_code, 302)

    def test_get_json_authenticated(self):
        self.client.login(username='alijundi', password='password123')
        response = self.client.get('/wardrobe/json/')
        self.assertEqual(response.status_code, 200)