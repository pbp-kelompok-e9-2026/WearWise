from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import ClothingReference
from .tests import DATA, item


@override_settings(CLIMATIQ_API_KEY='', PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class HtmxFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('htmx-buyer')
        cls.analyzer = get_user_model().objects.create_user('htmx-editor')
        cls.analyzer.groups.add(Group.objects.get(name='Analyzer'))
        cls.reference = ClothingReference.objects.create(
            clothing_name='Published cotton shirt', category='top', price=Decimal('300000'),
            source_name='Product label', is_published=True, created_by=cls.analyzer,
        )
        cls.draft = ClothingReference.objects.create(
            clothing_name='Private draft reference', category='top', price=Decimal('250000'),
            source_name='Draft label', created_by=cls.analyzer,
        )
        cls.analysis = item(owner=cls.user, material='cotton', weight_kg=Decimal('0.50'))
        cls.analysis.save()

    def url(self, name, obj=None):
        return reverse('worth_to_buy_analyzer:' + name, args=[obj.pk] if obj else None)

    def test_catalogue_fragment_is_private_and_full_page_remains_available(self):
        self.client.force_login(self.user)
        url = self.url('catalogue')
        response = self.client.get(url, {'q': 'cotton'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'id="catalogue-results"')
        self.assertContains(response, self.reference.clothing_name)
        self.assertNotContains(response, self.draft.clothing_name)
        self.assertNotContains(response, '<!DOCTYPE')
        self.assertIn('HX-Request', response.headers['Vary'])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertContains(self.client.get(url), '<!DOCTYPE')
        self.assertContains(self.client.get(url), 'hx-history="false"')

    def test_history_restore_returns_a_complete_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url('catalogue'), HTTP_HX_REQUEST='true', HTTP_HX_HISTORY_RESTORE_REQUEST='true')
        self.assertContains(response, '<!DOCTYPE')
        self.assertIn('HX-History-Restore-Request', response.headers['Vary'])

    def test_fragment_pagination_keeps_filters_and_target(self):
        for number in range(12):
            ClothingReference.objects.create(
                clothing_name=f'Cotton {number}', category='top', price=10000,
                source_name='Label', is_published=True,
            )
        self.client.force_login(self.user)
        response = self.client.get(self.url('catalogue'), {'q': 'Cotton', 'category': 'top'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'hx-target="#catalogue-results"')
        self.assertContains(response, 'q=Cotton&amp;category=top&amp;page=2')

    def test_anonymous_htmx_requests_redirect_the_entire_browser_to_login(self):
        for url in (self.url('catalogue'), self.url('reference_list')):
            response = self.client.get(url, HTTP_HX_REQUEST='true')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.headers['HX-Redirect'].startswith(reverse('main:login') + '?next='))
            self.assertEqual(response.content, b'')
        response = self.client.post(self.url('decide', self.analysis), {'decision': 'buy'}, HTTP_HX_REQUEST='true')
        self.assertIn('HX-Redirect', response.headers)

    def test_workspace_search_fragment_keeps_drafts_private_from_users(self):
        self.client.force_login(self.analyzer)
        response = self.client.get(self.url('reference_list'), {'status': 'draft'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'id="reference-results"')
        self.assertContains(response, self.draft.clothing_name)
        self.assertNotContains(response, self.reference.clothing_name)
        self.assertNotContains(response, '<!DOCTYPE')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url('reference_list'), HTTP_HX_REQUEST='true').status_code, 403)

    def test_publication_is_explicit_retryable_and_updates_filtered_results(self):
        self.client.force_login(self.analyzer)
        url = self.url('reference_publish', self.draft) + '?status=draft'
        for attempt in range(2):
            response = self.client.post(url, {'publication': 'publish'}, HTTP_HX_REQUEST='true')
            self.assertContains(response, 'Referensi diterbitkan')
            self.assertNotContains(response, self.draft.clothing_name)
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.is_published)
        self.assertEqual(self.draft.updated_by, self.analyzer)
        response = self.client.post(self.url('reference_publish', self.draft), {'publication': 'withdraw'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'ditarik dari katalog')
        self.draft.refresh_from_db()
        self.assertFalse(self.draft.is_published)

    def test_publication_rejects_get_invalid_state_and_other_roles(self):
        url = self.url('reference_publish', self.draft)
        self.client.force_login(self.analyzer)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'publication': 'invalid'}, HTTP_HX_REQUEST='true').status_code, 400)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(url, {'publication': 'publish'}, HTTP_HX_REQUEST='true').status_code, 403)
        self.draft.refresh_from_db()
        self.assertFalse(self.draft.is_published)

    def test_publication_keeps_the_url_in_sync_when_the_last_page_disappears(self):
        for number in range(12):
            ClothingReference.objects.create(
                clothing_name=f'Draft shirt {number}', category='top', price=10000,
                source_name='Label', is_published=False,
            )
        self.client.force_login(self.analyzer)
        response = self.client.post(
            self.url('reference_publish', self.draft) + '?status=draft&page=2',
            {'publication': 'publish'}, HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.headers['HX-Replace-Url'], self.url('reference_list') + '?status=draft&page=1')
        self.assertContains(response, 'Draft shirt')
        self.assertNotContains(response, self.draft.clothing_name)

    def test_publication_without_javascript_uses_normal_redirect(self):
        self.client.force_login(self.analyzer)
        response = self.client.post(self.url('reference_publish', self.draft), {'publication': 'publish'})
        self.assertRedirects(response, self.url('reference_list'))
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.is_published)

    def test_decision_saves_without_returning_or_caching_the_whole_page(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url('decide', self.analysis), {'decision': 'buy', 'decision_note': 'For everyday use'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'id="decision-panel"')
        self.assertContains(response, 'Keputusan berhasil disimpan.')
        self.assertNotContains(response, '<!DOCTYPE')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.decision, 'buy')
        self.assertIsNotNone(self.analysis.decided_at)
        self.assertNotContains(self.client.get(self.url('detail', self.analysis)), 'Keputusan berhasil disimpan.')

    def test_invalid_decision_returns_form_errors_without_mutating_data(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url('decide', self.analysis), {'decision': 'unknown'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'Keputusan belum tersimpan')
        self.assertNotContains(response, '<!DOCTYPE')
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.decision, 'undecided')

    def test_carbon_refresh_only_returns_carbon_panel(self):
        self.client.force_login(self.user)
        with patch('worth_to_buy_analyzer.services.compute_co2e', return_value=(Decimal('9.06'), 'fallback')):
            response = self.client.post(self.url('refresh_carbon', self.analysis), HTTP_HX_REQUEST='true')
        self.assertContains(response, 'id="carbon-panel"')
        self.assertNotContains(response, 'id="decision-panel"')
        self.assertNotContains(response, '<!DOCTYPE')
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.carbon_kg_co2e, Decimal('9.0600'))

    def test_htmx_cannot_bypass_csrf_or_private_object_ownership(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.analyzer)
        self.assertEqual(client.post(self.url('reference_publish', self.draft), {'publication': 'publish'}, HTTP_HX_REQUEST='true').status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url('decide', self.analysis), {'decision': 'buy'}, HTTP_HX_REQUEST='true').status_code, 403)
        other = get_user_model().objects.create_user('htmx-other-buyer')
        self.client.force_login(other)
        for name in ('decide', 'refresh_carbon'):
            self.assertEqual(self.client.post(self.url(name, self.analysis), {'decision': 'buy'}, HTTP_HX_REQUEST='true').status_code, 404)
