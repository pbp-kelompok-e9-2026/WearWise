from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth.models import User
from wardrobe.models import ClothingItem
from wardrobe.forms import ClothingItemForm

class ClothingItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alijundi', password='password123')
        self.item = ClothingItem.objects.create(
            user=self.user,
            name='Kaos Polos',
            category='TOP',
            material='Katun',
            price=100000.0,
            purchase_date='2026-01-01',
            wear_count=0
        )
    def test_calculate_cost_per_wear_zero_wear(self):
        self.assertEqual(self.item.calculate_cost_per_wear(), 100000.0)

    def test_calculate_cost_per_wear_positive_wear(self):
        self.item.wear_count = 4
        self.item.save()
        self.assertEqual(self.item.calculate_cost_per_wear(), 25000.0)

    def test_string_representation(self):
        self.assertEqual(str(self.item), "Kaos Polos (alijundi)")

class ClothingItemFormTest(TestCase):
    def test_valid_form(self):
        data = {
            'name': 'Celana Chino',
            'category': 'BOTTOM',
            'material': 'Twill',
            'price': 25000,
            'purchase_date': '2026-02-01',
            'image_url': 'https://example.com/chino.jpg'
        }
        form = ClothingItemForm(data=data)
        self.assertTrue(form.is_valid())

    def test_xss_sanitization_in_clean_methods(self):
        data = {
            'name': '<script>alert("xss")</script>Kemeja Batik',
            'category': 'TOP',
            'material': '<b>Sutra</b>',
            'price': 300000,
            'purchase_date': '2026-02-10',
            'image_url': ''
        }
        form = ClothingItemForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'alert("xss")Kemeja Batik')
        self.assertEqual(form.cleaned_data['material'], 'Sutra')

    def test_invalid_form_missing_required_fields(self):
        form = ClothingItemForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('category', form.errors)
        self.assertIn('price', form.errors)

    def WardrobeViewsTest(TestCase):
        def setUp(self):
            self.client = Client()
            self.user1 = User.objects.create_user(username='alijundi', password='password123')
            self.user2 = User.objects.create_user(username='otheruser', password='password123')

            self.item1 = ClothingItem.objects.create(
                user=self.user1,
                name='Jaket Parka',
                category='OUTER',
                material='Parasut',
                price=400000,
                purchase_date='2026-01-15',
                wear_count=2
            )

            self.item_user2 = ClothingItem.objects.create(
                user=self.user2,
                name='Topi Baseball',
                category='ACCESSORY',
                material='Katun',
                price=50000,
                purchase_date='2026-01-05',
                wear_count=1
            )

        def test_unauthenticated_user_redirect(self):
            response = self.client.get(reverse('wardrobe:show_wardrobe'))
            self.assertEqual(response.status_code, 302)

            response_json = self.client.get(reverse('wardrobe:get_wardrobe_json'))
            self.assertEqual(response_json.status_code, 302)

        def test_show_wardrobe_authenticated(self):
            self.client.login(username='alijundi', password='password123')
            response = self.client.get(reverse('wardrobe:show_wardrobe'))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'wardrobe.html')

        def test_get_wardrobe_json_authenticated(self):
            self.client.login(username='alijundi', password='password123')
            response = self.client.get(reverse('wardrobe:get_wardrobe_json'))
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(len(data),2)
            item_names = [item['fields']['name'] for item in data]
            self.assertIn('Jaket Parka', item_names)
            self.asserttNotIn('Topi Baseball', item_names)

        def test_get_wardrobe_json_category_filter(self):
            self.client.login(username='alijundi', password='password123')
            response = self.client.get(reverse('wardrobe:get_wardrobe_json') + '?category=OUTER')
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['fields']['name'], 'Jaket Parka')

        def test_add_clothing_ajax_success(self):
            self.client.login(username='alijundi', password='password123')
            post_data = {
                'name': 'Kaos Polo',
                'category': 'TOP',
                'material': 'Pique',
                'price': 150000,
                'purchase_date': '2026-02-01',
                'image_url': 'https://example.com/polo.jpg'
            }
            response = self.client.post(reverse('wardrobe:add_clothing_ajax'), post_data)
            self.assertEqual(response.status_code, 201)
            self.assertTrue(ClothingItem.objects.filter(name='Kaos Polo', user=self.user1).exists())

        def test_add_clothing_ajax_invalid(self):
            self.client.login(username='alijundi', password='password123')
            post_data = {'name': ''}  # Missing required fields
            response = self.client.post(reverse('wardrobe:add_clothing_ajax'), post_data)
            self.assertEqual(response.status_code, 400)

        def test_increment_wear_ajax_success(self):
            self.client.login(username='alijundi', password='password123')
            url = reverse('wardrobe:increment_wear_ajax', kwargs={'item_id': self.item1.id})
            response = self.client.post(url)
            self.assertEqual(response.status_code, 200)

            self.item1.refresh_from_db()
            self.assertEqual(self.item1.wear_count, 3)

        def test_increment_wear_other_user_item_fails(self):
            self.client.login(username='alijundi', password='password123')
            url = reverse('wardrobe:increment_wear_ajax', kwargs={'item_id': self.item_user2.id})
            response = self.client.post(url)
            self.assertEqual(response.status_code, 404)

        def test_delete_clothing_ajax_success(self):
            self.client.login(username='alijundi', password='password123')
            url = reverse('wardrobe:delete_clothing_ajax', kwargs={'item_id': self.item1.id})
            response = self.client.post(url)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(ClothingItem.objects.filter(id=self.item1.id).exists())

        def test_delete_clothing_other_user_item_fails(self):
            # User 1 mencoba menghapus item milik User 2
            self.client.login(username='alijundi', password='password123')
            url = reverse('wardrobe:delete_clothing_ajax', kwargs={'item_id': self.item_user2.id})
            response = self.client.post(url)
            self.assertEqual(response.status_code, 404)
            self.assertTrue(ClothingItem.objects.filter(id=self.item_user2.id).exists())
        
        