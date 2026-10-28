from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .forms import ClothingReferenceForm
from .models import ClothingReference, PurchaseAnalysis
from .tests import DATA, item


REFERENCE_DATA = {
    'clothing_name': 'Kemeja katun acuan', 'category': 'top', 'brand': 'Contoh',
    'product_url': 'https://example.com/kemeja', 'price': '300000',
    'material': 'cotton', 'weight_kg': '0.50', 'source_name': 'Label produk contoh',
    'notes': 'Periksa kembali harga saat membeli.',
}


@override_settings(CLIMATIQ_API_KEY='', PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AnalyzerRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user('buyer', password='testing-password')
        cls.analyzer = User.objects.create_user('reference-editor', password='testing-password')
        cls.analyzer.groups.add(Group.objects.get(name='Analyzer'))
        cls.other_analyzer = User.objects.create_user('reference-editor-two')
        cls.other_analyzer.groups.add(Group.objects.get(name='Analyzer'))
        cls.admin = User.objects.create_superuser('site-admin', password='testing-password')

    def url(self, name, obj=None):
        return reverse('worth_to_buy_analyzer:' + name, args=[obj.pk] if obj else None)

    def reference(self, **changes):
        return ClothingReference.objects.create(
            **{**REFERENCE_DATA, 'price': Decimal('300000'), 'weight_kg': Decimal('0.50'),
               'created_by': self.analyzer, 'updated_by': self.analyzer, **changes}
        )

    def login(self, user, next_url=None):
        data = {'username': user.username, 'password': 'testing-password'}
        if next_url is not None:
            data['next'] = next_url
        return self.client.post(reverse('main:login'), data)

    def test_login_destination_for_all_three_roles(self):
        for user, target in (
            (self.user, reverse('main:show_main')),
            (self.analyzer, self.url('reference_list')),
            (self.admin, reverse('admin:index')),
        ):
            with self.subTest(user=user.username):
                self.client.logout()
                self.assertRedirects(self.login(user), target)

    def test_analyzer_stale_and_unsafe_next_stays_in_workspace(self):
        for target in (self.url('create'), '/', 'https://example.com/', '//example.com/'):
            with self.subTest(next=target):
                self.client.logout()
                self.assertRedirects(self.login(self.analyzer, target), self.url('reference_list'))
        self.client.logout()
        self.assertRedirects(self.login(self.analyzer, self.url('reference_create')), self.url('reference_create'))

    def test_home_returns_analyzer_to_dedicated_menu(self):
        self.client.force_login(self.analyzer)
        self.assertRedirects(self.client.get('/'), self.url('reference_list'))
        page = self.client.get(self.url('reference_list'))
        self.assertContains(page, 'Menu Analyzer')
        self.assertNotContains(page, 'Koleksi analisis')
        self.assertFalse(self.analyzer.is_staff)
        self.assertFalse(self.analyzer.is_superuser)

    def test_anonymous_workspace_requires_login(self):
        target = self.url('reference_list')
        self.assertRedirects(self.client.get(target), reverse('main:login') + '?next=' + target)

    def test_user_and_plain_staff_cannot_access_or_mutate_references(self):
        obj = self.reference()
        for staff in (False, True):
            self.user.is_staff = staff
            self.user.save(update_fields=['is_staff'])
            self.client.force_login(self.user)
            for name, record in (
                ('reference_list', None), ('reference_create', None),
                ('reference_detail', obj), ('reference_update', obj), ('reference_delete', obj),
            ):
                with self.subTest(staff=staff, route=name):
                    self.assertEqual(self.client.get(self.url(name, record)).status_code, 403)
                    self.assertEqual(self.client.post(self.url(name, record), REFERENCE_DATA).status_code, 403)
        self.assertEqual(ClothingReference.objects.count(), 1)

    def test_role_revocation_blocks_access_immediately(self):
        self.client.force_login(self.analyzer)
        self.assertEqual(self.client.get(self.url('reference_list')).status_code, 200)
        self.analyzer.groups.clear()
        self.assertEqual(self.client.get(self.url('reference_list')).status_code, 403)

    def test_registration_cannot_choose_a_privileged_role(self):
        self.client.post(reverse('main:register'), {
            'username': 'new-member', 'password1': 'Example-password-2026!',
            'password2': 'Example-password-2026!', 'role': 'Analyzer',
            'groups': Group.objects.get(name='Analyzer').pk, 'is_staff': '1', 'is_superuser': '1',
        })
        account = get_user_model().objects.get(username='new-member')
        self.assertFalse(account.groups.exists())
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)

    def test_analyzer_cannot_read_users_private_analysis(self):
        obj = item(owner=self.user)
        obj.save()
        self.client.force_login(self.analyzer)
        for name, record in (('analyzer', None), ('create', None), ('catalogue', None),
                             ('detail', obj), ('update', obj), ('delete', obj)):
            self.assertEqual(self.client.get(self.url(name, record)).status_code, 403)
        for name in ('update', 'delete', 'decide', 'refresh_carbon'):
            self.assertEqual(self.client.post(self.url(name, obj), DATA).status_code, 403)
        obj.refresh_from_db()
        self.assertEqual(obj.owner, self.user)

    def test_create_tracks_author_and_draft_is_default(self):
        self.client.force_login(self.analyzer)
        response = self.client.post(self.url('reference_create'), {
            **REFERENCE_DATA, 'created_by': self.admin.pk, 'updated_by': self.admin.pk,
        })
        obj = ClothingReference.objects.get()
        self.assertRedirects(response, self.url('reference_detail', obj))
        self.assertEqual(obj.created_by, self.analyzer)
        self.assertEqual(obj.updated_by, self.analyzer)
        self.assertFalse(obj.is_published)
        self.assertEqual(PurchaseAnalysis.objects.count(), 0)

    def test_shared_reference_edit_preserves_original_author(self):
        obj = self.reference()
        self.client.force_login(self.other_analyzer)
        response = self.client.post(self.url('reference_update', obj), {
            **REFERENCE_DATA, 'price': '350000', 'is_published': 'on', 'created_by': self.admin.pk,
        })
        self.assertRedirects(response, self.url('reference_detail', obj))
        obj.refresh_from_db()
        self.assertEqual(obj.price, Decimal('350000'))
        self.assertTrue(obj.is_published)
        self.assertEqual(obj.created_by, self.analyzer)
        self.assertEqual(obj.updated_by, self.other_analyzer)

    def test_invalid_reference_does_not_create_or_overwrite_data(self):
        self.client.force_login(self.analyzer)
        response = self.client.post(self.url('reference_create'), {**REFERENCE_DATA, 'source_name': ''})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClothingReference.objects.exists())
        obj = self.reference()
        response = self.client.post(self.url('reference_update', obj), {**REFERENCE_DATA, 'price': '-1'})
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.price, Decimal('300000'))
        for changes in ({'product_url': 'javascript:alert(1)'}, {'weight_kg': ''}, {'material': ''},
                        {'price': 'NaN'}, {'weight_kg': '0'}):
            with self.subTest(changes=changes):
                self.assertFalse(ClothingReferenceForm(REFERENCE_DATA | changes).is_valid())

    def test_published_catalogue_hides_drafts_and_prefills_only_product_data(self):
        published = self.reference(is_published=True)
        draft = self.reference(clothing_name='Confidential draft')
        self.client.force_login(self.user)
        response = self.client.get(self.url('catalogue'), {'status': 'draft'})
        self.assertContains(response, published.clothing_name)
        self.assertNotContains(response, draft.clothing_name)
        response = self.client.get(self.url('create'), {'reference': published.pk})
        form = response.context['form']
        self.assertEqual(form['price'].value(), Decimal('300000'))
        self.assertEqual(form['clothing_name'].value(), published.clothing_name)
        self.assertIsNone(form['budget'].value())
        self.assertIsNone(form['expected_wears'].value())
        for reference in (draft.pk, 'bad', '-1', '999999999999999999999999999999'):
            self.assertEqual(self.client.get(self.url('create'), {'reference': reference}).status_code, 404)
        self.assertEqual(PurchaseAnalysis.objects.count(), 0)

    def test_saved_analysis_is_independent_of_reference_updates_or_removal(self):
        reference = self.reference(is_published=True)
        self.client.force_login(self.user)
        response = self.client.post(self.url('create') + '?reference=' + str(reference.pk), DATA)
        analysis = PurchaseAnalysis.objects.get()
        self.assertRedirects(response, self.url('detail', analysis))
        self.client.force_login(self.analyzer)
        self.client.post(self.url('reference_update', reference), {**REFERENCE_DATA, 'price': '900000'})
        self.assertContains(self.client.get(self.url('reference_delete', reference)), 'Hapus referensi ini?')
        self.assertTrue(ClothingReference.objects.filter(pk=reference.pk).exists())
        self.assertEqual(self.client.delete(self.url('reference_delete', reference)).status_code, 405)
        self.assertRedirects(self.client.post(self.url('reference_delete', reference)), self.url('reference_list'))
        analysis.refresh_from_db()
        self.assertEqual(analysis.price, Decimal('300000'))
        self.assertEqual(analysis.owner, self.user)
        # A user may still submit copied inputs from an already-open form.
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(self.url('create') + '?reference=' + str(reference.pk), DATA).status_code, 302)

    def test_search_status_and_pagination_for_workspace_and_catalogue(self):
        for i in range(13):
            self.reference(clothing_name=f'Published {i}', is_published=True)
        self.reference(clothing_name='Draft only')
        self.client.force_login(self.analyzer)
        response = self.client.get(self.url('reference_list'), {'status': 'draft'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.client.force_login(self.user)
        response = self.client.get(self.url('catalogue'), {'q': 'Published', 'category': 'top'})
        self.assertEqual(response.context['page_obj'].paginator.count, 13)
        self.assertEqual(len(response.context['page_obj']), 12)
        self.assertEqual(len(self.client.get(self.url('catalogue'), {'page': 2}).context['page_obj']), 1)
        self.assertEqual(self.client.get(self.url('catalogue'), {'page': 'bad'}).status_code, 200)

    def test_csrf_and_http_methods_guard_reference_mutations(self):
        obj = self.reference()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.analyzer)
        for name, record in (('reference_create', None), ('reference_update', obj), ('reference_delete', obj)):
            self.assertEqual(client.post(self.url(name, record), REFERENCE_DATA).status_code, 403)
        self.assertEqual(client.post(self.url('reference_detail', obj)).status_code, 403)
        self.client.force_login(self.analyzer)
        self.assertEqual(self.client.post(self.url('reference_list')).status_code, 405)
        self.assertEqual(self.client.post(self.url('reference_detail', obj)).status_code, 405)
        self.assertEqual(self.client.put(self.url('reference_create'), REFERENCE_DATA).status_code, 405)
        client.get(self.url('reference_create'))
        token = client.cookies['csrftoken'].value
        response = client.post(self.url('reference_create'), {**REFERENCE_DATA, 'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 302)

    def test_reference_text_is_escaped(self):
        obj = self.reference(clothing_name='<script>alert(1)</script>', is_published=True)
        self.client.force_login(self.analyzer)
        response = self.client.get(self.url('reference_detail', obj))
        self.assertNotContains(response, obj.clothing_name)
        self.assertContains(response, '&lt;script&gt;')
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(self.url('catalogue')), obj.clothing_name)

    def test_superuser_can_manage_reference_without_analyzer_membership(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url('reference_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:worth_to_buy_analyzer_clothingreference_changelist')).status_code, 200)
