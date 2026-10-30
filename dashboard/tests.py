from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from dashboard.forms import (
    DeleteAccountForm,
    ProfileDetailForm,
    ProfileForm,
)
from dashboard.models import Profile
from wardrobe.models import ClothingItem

User = get_user_model()

class DashboardBaseTest(TestCase):
    """Setup dasar: user login + profile otomatis."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='rahasia12345',
            first_name='Alice',
            last_name='Wonder',
        )
        self.profile = Profile.objects.create(
            user=self.user,
            phone='+62 812 3456 7890',
            address='Jl. Merdeka No. 1, Jakarta',
        )
        self.client.login(username='alice', password='rahasia12345')

    def _make_item(self, name='Kemeja', price=100000, wear_count=10):
        return ClothingItem.objects.create(
            user=self.user,
            name=name,
            category='TOP',
            material='cotton',
            price=price,
            purchase_date='2026-01-10',
            wear_count=wear_count,
        )

# TEST: SHOW PROFILE

class ShowProfileTest(DashboardBaseTest):

    def test_login_required_redirect(self):
        """User belum login → diarahkan ke halaman login."""
        self.client.logout()
        response = self.client.get(reverse('dashboard:show_profile'))
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('/login/', response.url)

    def test_show_profile_200(self):
        response = self.client.get(reverse('dashboard:show_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/profile.html')

    def test_auto_create_profile_if_missing(self):
        """Kalau Profile belum ada, get_or_create bikin otomatis."""
        Profile.objects.filter(user=self.user).delete()
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

        self.client.get(reverse('dashboard:show_profile'))
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_stats_empty_wardrobe(self):
        """Tanpa clothing item → semua statistik nol, tidak crash."""
        response = self.client.get(reverse('dashboard:show_profile'))
        self.assertEqual(response.context['wears_logged'], 0)
        self.assertEqual(response.context['avg_cost_per_wear'], 0)
        self.assertEqual(response.context['sustainability_score'], 0)

    def test_stats_with_items(self):
        """Dengan 2 item → cek perhitungan agregat."""
        self._make_item(name='Kemeja', price=100000, wear_count=20)
        self._make_item(name='Celana', price=200000, wear_count=40)

        response = self.client.get(reverse('dashboard:show_profile'))

        # total wears = 60
        self.assertEqual(response.context['wears_logged'], 60)
        # total spent = 300000, avg = 300000 / 60 = 5000
        self.assertEqual(response.context['avg_cost_per_wear'], 5000)
        # score = (60 / 2) / 30 * 100 = 100 → capped 100
        self.assertEqual(response.context['sustainability_score'], 100)

    def test_sustainability_score_capped_at_100(self):
        """Wears sangat banyak → score tetap max 100."""
        self._make_item(wear_count=1000)
        response = self.client.get(reverse('dashboard:show_profile'))
        self.assertEqual(response.context['sustainability_score'], 100)

    def test_sustainability_score_partial(self):
        """1 item, 15 wears → (15/1)/30 * 100 = 50."""
        self._make_item(wear_count=15)
        response = self.client.get(reverse('dashboard:show_profile'))
        self.assertEqual(response.context['sustainability_score'], 50)

    def test_only_count_own_items(self):
        """Item user lain tidak ikut dihitung."""
        other = User.objects.create_user(username='bob', password='x')
        ClothingItem.objects.create(
            user=other,
            name='Kaos',
            category='TOP',
            material='cotton',
            price=999,
            purchase_date='2026-01-10',
            wear_count=99,
        )

        response = self.client.get(reverse('dashboard:show_profile'))
        self.assertEqual(response.context['wears_logged'], 0)

# TEST: EDIT PROFILE

class EditProfileTest(DashboardBaseTest):

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('dashboard:edit_profile'))
        self.assertIn('/login/', response.url)

    def test_get_edit_profile_200(self):
        response = self.client.get(reverse('dashboard:edit_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/edit_profile.html')
        self.assertIn('user_form', response.context)
        self.assertIn('detail_form', response.context)

    def test_edit_profile_success(self):
        response = self.client.post(reverse('dashboard:edit_profile'), {
            'first_name': 'Alicia',
            'last_name': 'Keys',
            'email': 'alicia@example.com',
            'phone': '+62 811 1111 1111',
            'address': 'Jl. Baru No. 2',
        })
        self.assertRedirects(response, reverse('dashboard:show_profile'))

        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alicia')
        self.assertEqual(self.user.email, 'alicia@example.com')
        self.assertEqual(self.profile.phone, '+62 811 1111 1111')
        self.assertEqual(self.profile.address, 'Jl. Baru No. 2')

    def test_edit_profile_duplicate_email_rejected(self):
        """Email yang dipakai user lain → ditolak."""
        User.objects.create_user(
            username='bob', email='bob@example.com', password='x'
        )
        response = self.client.post(reverse('dashboard:edit_profile'), {
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'email': 'bob@example.com',   # sudah dipakai
            'phone': '+62 812 3456 7890',
            'address': 'Jl. Merdeka',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['user_form'],
            'email',
            'This email is already used by another account.',
        )
        # Email lama tetap
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'alice@example.com')

    def test_edit_profile_same_email_allowed(self):
        """Email milik sendiri → boleh (tidak dianggap duplikat)."""
        response = self.client.post(reverse('dashboard:edit_profile'), {
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'email': 'alice@example.com',   # milik sendiri
            'phone': '+62 812 3456 7890',
            'address': 'Jl. Merdeka',
        })
        self.assertRedirects(response, reverse('dashboard:show_profile'))

    def test_edit_profile_invalid_phone_rejected(self):
        """Format phone ngawur → error."""
        response = self.client.post(reverse('dashboard:edit_profile'), {
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'email': 'alice@example.com',
            'phone': 'abc-def',   # invalid
            'address': 'Jl. Merdeka',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('phone', response.context['detail_form'].errors)

    def test_edit_profile_phone_optional(self):
        """Phone kosong boleh karena required=False."""
        response = self.client.post(reverse('dashboard:edit_profile'), {
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'email': 'alice@example.com',
            'phone': '',
            'address': 'Jl. Merdeka',
        })
        self.assertRedirects(response, reverse('dashboard:show_profile'))

# TEST: DELETE ACCOUNT

class DeleteAccountTest(DashboardBaseTest):

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('dashboard:delete_account'))
        self.assertIn('/login/', response.url)

    def test_get_delete_account_200(self):
        response = self.client.get(reverse('dashboard:delete_account'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/delete_account.html')

    def test_get_shows_item_count(self):
        self._make_item()
        self._make_item(name='Kaos')
        response = self.client.get(reverse('dashboard:delete_account'))
        self.assertEqual(response.context['item_count'], 2)

    def test_delete_wrong_password(self):
        """Password salah → akun tidak terhapus."""
        response = self.client.post(reverse('dashboard:delete_account'), {
            'password': 'salahbanget',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('password', response.context['form'].errors)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_delete_correct_password(self):
        """Password benar → akun, profile, item semua terhapus."""
        self._make_item()

        response = self.client.post(reverse('dashboard:delete_account'), {
            'password': 'rahasia12345',
        })
        self.assertRedirects(response, reverse('main:show_main'))

        self.assertFalse(User.objects.filter(username='alice').exists())
        self.assertFalse(Profile.objects.filter(user_id=self.user.pk).exists())
        self.assertFalse(ClothingItem.objects.filter(user_id=self.user.pk).exists())

    def test_delete_logs_out(self):
        """Setelah delete, session login hilang."""
        self.client.post(reverse('dashboard:delete_account'), {
            'password': 'rahasia12345',
        })
        response = self.client.get(reverse('dashboard:show_profile'))
        self.assertIn('/login/', response.url)

# TEST: FORMS

class ProfileFormTest(TestCase):

    def test_valid(self):
        form = ProfileForm(data={
            'first_name': 'A', 'last_name': 'B', 'email': 'a@b.com',
        })
        self.assertTrue(form.is_valid())

    def test_duplicate_email(self):
        User.objects.create_user(username='bob', email='bob@example.com')
        user2 = User.objects.create_user(username='carol', email='carol@example.com')
        form = ProfileForm(
            data={'first_name': 'C', 'last_name': 'D', 'email': 'bob@example.com'},
            instance=user2,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_clean_email_strips_whitespace(self):
        form = ProfileForm(data={
            'first_name': 'A', 'last_name': 'B', 'email': '  a@b.com  ',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'a@b.com')


class ProfileDetailFormTest(TestCase):

    def test_phone_valid_formats(self):
        for phone in ['+62 812 3456 7890', '0812345678', '0812-3456-7890']:
            form = ProfileDetailForm(data={'phone': phone, 'address': ''})
            self.assertTrue(form.is_valid(), f"Format {phone} harusnya valid")

    def test_phone_invalid_formats(self):
        for phone in ['abc', '123', '++62', 'phone!']:
            form = ProfileDetailForm(data={'phone': phone, 'address': ''})
            self.assertFalse(form.is_valid(), f"Format {phone} harusnya invalid")

    def test_phone_optional(self):
        form = ProfileDetailForm(data={'phone': '', 'address': ''})
        self.assertTrue(form.is_valid())


class DeleteAccountFormTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', password='rahasia12345'
        )

    def test_correct_password(self):
        form = DeleteAccountForm(
            data={'password': 'rahasia12345'}, user=self.user
        )
        self.assertTrue(form.is_valid())

    def test_wrong_password(self):
        form = DeleteAccountForm(
            data={'password': 'salah'}, user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)