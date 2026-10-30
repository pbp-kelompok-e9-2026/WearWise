from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from worth_to_buy_analyzer.models import ClothingReference, PurchaseAnalysis


class PageActions(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.links, self.forms, self.buttons, self.ids = [], [], [], set()
        self.current_form = None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href'))
        elif tag == 'form':
            self.current_form = attrs
            self.forms.append(attrs)
        elif tag == 'button':
            self.buttons.append((attrs, self.current_form))

    def handle_endtag(self, tag):
        if tag == 'form':
            self.current_form = None


@override_settings(CLIMATIQ_API_KEY='', PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class NavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('navigation-buyer')
        cls.analyzer = get_user_model().objects.create_user('navigation-editor')
        cls.analyzer.groups.add(Group.objects.get(name='Analyzer'))
        cls.analysis = PurchaseAnalysis.objects.create(
            owner=cls.user, clothing_name='Kemeja', category='top', price=300000,
            budget=400000, expected_wears=60, target_cpw=10000,
            existing_clothing='none', purpose='routine', material='cotton', weight_kg='0.50',
        )
        cls.reference = ClothingReference.objects.create(
            clothing_name='Kemeja referensi', category='top', price=300000,
            source_name='Label produk', is_published=True, created_by=cls.analyzer,
        )

    def assert_page_actions_work(self, url, check_buttons=False, response=None):
        response = response if response is not None else self.client.get(url)
        self.assertEqual(response.status_code, 200)
        page = PageActions(response.content.decode())
        for href in set(page.links):
            with self.subTest(page=url, href=href):
                self.assertTrue(href, 'Tautan tidak memiliki tujuan')
                self.assertNotEqual(href, '#', 'Tautan masih berupa placeholder')
                target = urlsplit(urljoin(url, href))
                self.assertIn(target.scheme, ('', 'http', 'https'))
                if target.netloc:
                    continue
                resolve(target.path)
                if target.fragment and target.path == urlsplit(url).path:
                    self.assertIn(unquote(target.fragment), page.ids)
                destination = target.path + ('?' + target.query if target.query else '')
                self.assertEqual(self.client.get(destination, follow=True).status_code, 200)
        for form in page.forms:
            resolve(urlsplit(urljoin(url, form.get('action') or url)).path)
        if check_buttons:
            for button, form in page.buttons:
                with self.subTest(page=url, button=button):
                    if button.get('type', 'submit') == 'submit':
                        self.assertIsNotNone(form, 'Tombol submit harus terhubung ke form')
                    else:
                        self.assertEqual(button.get('id'), 'ww-toggle')
                        self.assertIn(button.get('aria-controls'), page.ids)
        return page

    def test_public_navigation_and_footer_have_real_destinations(self):
        for name in ('main:show_main', 'main:about', 'main:login', 'main:register'):
            self.assert_page_actions_work(reverse(name))
        footer = self.client.get(reverse('main:about'))
        self.assertContains(footer, 'href="' + reverse('worth_to_buy_analyzer:analyzer') + '"')
        self.assertContains(footer, 'href="' + reverse('wardrobe:show_wardrobe') + '"')

    def test_user_navigation_and_all_purchase_pages_are_connected(self):
        self.client.force_login(self.user)
        for name in ('analyzer', 'create', 'catalogue', 'detail', 'update', 'delete'):
            url = reverse('worth_to_buy_analyzer:' + name, args=[self.analysis.pk] if name in ('detail', 'update', 'delete') else None)
            self.assert_page_actions_work(url, check_buttons=True)
        response = self.client.get(reverse('worth_to_buy_analyzer:analyzer'))
        for name in ('wardrobe:show_wardrobe', 'lifecycle:index', 'dashboard:edit_profile'):
            self.assertContains(response, 'href="' + reverse(name) + '"')
        self.assertNotContains(response, '>Settings</a>')

    def test_analyzer_pages_and_published_reference_are_connected(self):
        self.client.force_login(self.analyzer)
        for name in ('reference_list', 'reference_create', 'reference_detail', 'reference_update', 'reference_delete'):
            url = reverse('worth_to_buy_analyzer:' + name, args=[self.reference.pk] if name in ('reference_detail', 'reference_update', 'reference_delete') else None)
            self.assert_page_actions_work(url, check_buttons=True)
        self.client.force_login(self.user)
        self.assert_page_actions_work(reverse('worth_to_buy_analyzer:create') + '?reference=' + str(self.reference.pk), check_buttons=True)

    def test_validation_error_links_point_to_existing_inputs(self):
        self.client.force_login(self.user)
        url = reverse('worth_to_buy_analyzer:create')
        self.assert_page_actions_work(url, check_buttons=True, response=self.client.post(url, {}))
