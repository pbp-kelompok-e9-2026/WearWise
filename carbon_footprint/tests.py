import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from . import services
import uuid

from .constants import (
    CATEGORY_CHOICES,
    CATEGORY_WEIGHT_KG,
    FALLBACK_DEFAULT_KG_CO2E_PER_KG,
    FALLBACK_KG_CO2E_PER_KG,
    MATERIAL_CHOICES,
    MONEY_FACTOR_ID,
    SCORE_MAX_CO2E_PER_WEAR,
)
from .access import ANALYZER_GROUP, can_open_analyzer, is_analyzer
from .analysis import build_analysis
from .models import CarbonEstimate, CategoryWeight, MaterialFactor

User = get_user_model()

FORM = {
    "name": "Oversized Cotton Shirt",
    "category": "shirt",
    "material": "cotton",
    "weight_kg": "",
    "price": "300000",
    "estimated_wears": "24",
}


def fallback_co2e(material, weight):
    """Hasil yang diharapkan dari tabel cadangan: berat dikali kg CO2e per kg material.

    Dihitung dari constants.py supaya test tidak ikut pecah saat angkanya diperbarui.
    """
    return Decimal(str(round(float(weight) * FALLBACK_KG_CO2E_PER_KG[material], 2)))


def fake_response(payload):
    resp = mock.Mock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


@override_settings(CLIMATIQ_API_KEY="")
class OfflineTestCase(TestCase):
    """Dasar untuk test yang tidak boleh memakai API key asli atau menyentuh jaringan.

    API key dikosongkan walau environment-mu memilikinya, dan setiap panggilan
    requests.post yang lolos akan membuat test gagal. Test yang butuh jalur
    Climatiq memakai override_settings dan mock sendiri.
    """

    def setUp(self):
        super().setUp()
        guard = mock.patch.object(
            services.requests, "post", side_effect=AssertionError("Test memanggil jaringan sungguhan")
        )
        guard.start()
        self.addCleanup(guard.stop)


class ConstantsTests(TestCase):
    """Menjaga constants.py tetap konsisten, supaya salah ketik ketahuan sebelum jadi bug."""

    def test_every_material_has_a_fallback_rate_and_no_extras(self):
        materials = {value for value, _label in MATERIAL_CHOICES}
        self.assertEqual(materials, set(FALLBACK_KG_CO2E_PER_KG))

    def test_every_category_has_a_default_weight_and_no_extras(self):
        categories = {value for value, _label in CATEGORY_CHOICES}
        self.assertEqual(categories, set(CATEGORY_WEIGHT_KG))

    def test_numbers_are_positive(self):
        values = [*FALLBACK_KG_CO2E_PER_KG.values(), *CATEGORY_WEIGHT_KG.values(),
                  FALLBACK_DEFAULT_KG_CO2E_PER_KG, SCORE_MAX_CO2E_PER_WEAR]
        self.assertTrue(all(v > 0 for v in values))

    def test_money_factor_id_is_a_uuid(self):
        uuid.UUID(MONEY_FACTOR_ID)


class ScoreTests(TestCase):
    def test_score_matches_design_example(self):
        # Desain Figma: 3.2 kg CO2e, 24 wears -> skor 82
        self.assertEqual(services.sustainability_score(3.2, 24), 82)

    def test_score_is_clamped(self):
        self.assertEqual(services.sustainability_score(500, 1), 0)
        self.assertEqual(services.sustainability_score(0, 10), 100)


class EstimateMoneyTests(TestCase):
    def test_request_shape_and_parsing(self):
        # Bentuk respons mengikuti hasil uji nyata ke Climatiq (Rp300.000 -> 4.69 kg).
        payload = {"co2e": 4.6901506835, "co2e_unit": "kg"}
        with mock.patch.object(services.requests, "post", return_value=fake_response(payload)) as post:
            co2e = services.estimate_money_co2e(MONEY_FACTOR_ID, Decimal("300000"), "idr")
        self.assertAlmostEqual(co2e, 4.69, places=2)
        self.assertEqual(post.call_args.kwargs["json"], {
            "emission_factor": {"id": MONEY_FACTOR_ID},
            "parameters": {"money": 300000.0, "money_unit": "idr"},
        })

    def test_rejects_non_positive_and_unexpected_unit(self):
        for payload in ({"co2e": -1, "co2e_unit": "kg"}, {"co2e": 3, "co2e_unit": "t"}, {}):
            with mock.patch.object(services.requests, "post", return_value=fake_response(payload)):
                with self.assertRaises(services.ClimatiqError):
                    services.estimate_money_co2e(MONEY_FACTOR_ID, 100, "idr")


class ComputeTests(OfflineTestCase):
    def test_fallback_without_api_key(self):
        co2e, source = services.compute_co2e("cotton", Decimal("0.5"), Decimal("300000"))
        self.assertEqual(source, services.SOURCE_FALLBACK)
        self.assertEqual(co2e, fallback_co2e("cotton", Decimal("0.5")))

    def test_unknown_material_uses_default_rate(self):
        # Data lama bisa berisi material yang sudah dihapus dari MATERIAL_CHOICES.
        co2e, source = services.compute_co2e("linen", Decimal("1"), None)
        self.assertEqual(source, services.SOURCE_FALLBACK)
        self.assertEqual(co2e, Decimal(str(round(FALLBACK_DEFAULT_KG_CO2E_PER_KG, 2))))

    @override_settings(CLIMATIQ_API_KEY="test")
    def test_uses_climatiq_when_price_and_key_exist(self):
        with mock.patch.object(services, "estimate_money_co2e", return_value=4.69) as call:
            co2e, source = services.compute_co2e("cotton", Decimal("0.4"), Decimal("300000"))
        call.assert_called_once_with(MONEY_FACTOR_ID, Decimal("300000"), "idr")
        self.assertEqual((co2e, source), (Decimal("4.69"), services.SOURCE_CLIMATIQ))

    @override_settings(CLIMATIQ_API_KEY="test")
    def test_falls_back_without_price_even_with_key(self):
        with mock.patch.object(services, "estimate_money_co2e") as call:
            _co2e, source = services.compute_co2e("cotton", Decimal("0.4"), None)
        call.assert_not_called()
        self.assertEqual(source, services.SOURCE_FALLBACK)

    @override_settings(CLIMATIQ_API_KEY="test")
    def test_falls_back_when_climatiq_fails(self):
        with mock.patch.object(services, "estimate_money_co2e", side_effect=services.ClimatiqError("boom")):
            _co2e, source = services.compute_co2e("cotton", Decimal("0.4"), Decimal("300000"))
        self.assertEqual(source, services.SOURCE_FALLBACK)


class CrudTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("zidan", password="pw")
        self.other = User.objects.create_user("budi", password="pw")
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        resp = self.client.get(reverse("carbon_footprint:list"))
        self.assertEqual(resp.status_code, 302)

    def test_create_uses_category_weight_and_computes_co2e(self):
        resp = self.client.post(reverse("carbon_footprint:create"), FORM)
        self.assertRedirects(resp, reverse("carbon_footprint:list"))
        obj = CarbonEstimate.objects.get()
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.weight_kg, Decimal("0.25"))     # berat default kategori shirt
        self.assertEqual(obj.co2e_kg, fallback_co2e("cotton", Decimal("0.25")))   # tabel cadangan, tanpa API key
        self.assertEqual(obj.source, services.SOURCE_FALLBACK)

    @override_settings(CLIMATIQ_API_KEY="test")
    def test_create_with_price_uses_climatiq(self):
        with mock.patch.object(services, "estimate_money_co2e", return_value=4.69):
            self.client.post(reverse("carbon_footprint:create"), FORM)
        obj = CarbonEstimate.objects.get()
        self.assertEqual((obj.co2e_kg, obj.source), (Decimal("4.69"), services.SOURCE_CLIMATIQ))

    def test_create_rejects_invalid_input(self):
        resp = self.client.post(reverse("carbon_footprint:create"), {**FORM, "weight_kg": "-1", "estimated_wears": "0"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CarbonEstimate.objects.count(), 0)

    def test_update_recomputes_only_when_inputs_change(self):
        self.client.post(reverse("carbon_footprint:create"), FORM)
        obj = CarbonEstimate.objects.get()
        url = reverse("carbon_footprint:update", args=[obj.pk])
        with mock.patch("carbon_footprint.forms.compute_co2e", return_value=(Decimal("9.99"), "fallback")) as call:
            self.client.post(url, {**FORM, "weight_kg": "0.25", "name": "Renamed", "estimated_wears": "30"})
            call.assert_not_called()                      # nama dan wears tidak memengaruhi emisi
            self.client.post(url, {**FORM, "weight_kg": "0.25", "price": "350000"})
            self.assertEqual(call.call_count, 1)          # harga berubah
            self.client.post(url, {**FORM, "weight_kg": "1.00", "price": "350000"})
            self.assertEqual(call.call_count, 2)          # berat berubah
        obj.refresh_from_db()
        self.assertEqual(obj.co2e_kg, Decimal("9.99"))

    def test_cannot_touch_other_users_estimate(self):
        obj = CarbonEstimate.objects.create(user=self.other, name="x", category="shirt", material="cotton",
                                            weight_kg=Decimal("0.2"), co2e_kg=Decimal("1"))
        for name in ("update", "delete"):
            self.assertEqual(self.client.get(reverse(f"carbon_footprint:{name}", args=[obj.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("carbon_footprint:delete", args=[obj.pk])).status_code, 404)
        self.assertTrue(CarbonEstimate.objects.filter(pk=obj.pk).exists())

    def test_delete_requires_post(self):
        self.client.post(reverse("carbon_footprint:create"), FORM)
        obj = CarbonEstimate.objects.get()
        url = reverse("carbon_footprint:delete", args=[obj.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(CarbonEstimate.objects.exists())
        self.client.post(url)
        self.assertFalse(CarbonEstimate.objects.exists())

    def test_numbers_page_shows_item_stats(self):
        self.client.post(reverse("carbon_footprint:create"), FORM)
        resp = self.client.get(reverse("carbon_footprint:index"))
        self.assertContains(resp, "Oversized Cotton Shirt")
        self.assertContains(resp, "Rp")
        self.assertContains(resp, "CEDA 2025")                     # catatan sumber data
        self.assertEqual(resp.context["stats"]["wears"], 24)
        self.assertEqual(resp.context["stats"]["cost_per_wear"], 12500)   # 300000 / 24 wears

    def test_numbers_page_empty_state(self):
        resp = self.client.get(reverse("carbon_footprint:index"))
        self.assertContains(resp, "No estimates yet")



HX = {"HTTP_HX_REQUEST": "true"}


class HtmxTests(OfflineTestCase):
    """Permintaan HTMX mendapat potongan HTML; permintaan biasa tetap mendapat halaman penuh."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("zidan", password="pw")
        self.other = User.objects.create_user("budi", password="pw")
        self.client.force_login(self.user)
        self.shirt = self.make("Linen Shirt", "cotton", "shirt", "1.5")
        self.jacket = self.make("Wool Jacket", "wool", "jacket", "4.0")
        self.theirs = CarbonEstimate.objects.create(
            user=self.other, name="Secret Dress", category="dress", material="silk",
            weight_kg=Decimal("0.3"), co2e_kg=Decimal("2"))

    def make(self, name, material, category, co2e):
        return CarbonEstimate.objects.create(
            user=self.user, name=name, category=category, material=material,
            weight_kg=Decimal("0.5"), co2e_kg=Decimal(co2e))

    def names(self, resp):
        return [e.name for e in resp.context["estimates"]]

    # ----- daftar -----

    def test_list_returns_full_page_without_htmx(self):
        resp = self.client.get(reverse("carbon_footprint:list"))
        self.assertTemplateUsed(resp, "carbon_footprint/list.html")
        self.assertContains(resp, 'id="cf-filters"')

    def test_list_returns_only_rows_for_htmx(self):
        resp = self.client.get(reverse("carbon_footprint:list"), **HX)
        self.assertTemplateUsed(resp, "carbon_footprint/_rows.html")
        self.assertTemplateNotUsed(resp, "carbon_footprint/list.html")
        self.assertNotContains(resp, "<html")
        self.assertContains(resp, "Wool Jacket")

    def test_history_restore_gets_full_page(self):
        resp = self.client.get(reverse("carbon_footprint:list"), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertTemplateUsed(resp, "carbon_footprint/list.html")

    def test_list_varies_on_hx_request_header(self):
        resp = self.client.get(reverse("carbon_footprint:list"))
        self.assertIn("HX-Request", resp["Vary"])

    def test_search_filters_by_name_case_insensitive(self):
        resp = self.client.get(reverse("carbon_footprint:list"), {"q": "WOOL"}, **HX)
        self.assertEqual(self.names(resp), ["Wool Jacket"])

    def test_filter_by_material(self):
        resp = self.client.get(reverse("carbon_footprint:list"), {"material": "cotton"}, **HX)
        self.assertEqual(self.names(resp), ["Linen Shirt"])

    def test_unknown_material_and_sort_are_ignored(self):
        resp = self.client.get(reverse("carbon_footprint:list"), {"material": "unobtainium", "sort": "'; drop"}, **HX)
        self.assertEqual(len(self.names(resp)), 2)
        self.assertEqual(resp.context["filters"], {"q": "", "material": "", "sort": "newest"})

    def test_sorting(self):
        url = reverse("carbon_footprint:list")
        self.assertEqual(self.names(self.client.get(url, {"sort": "co2e_desc"}, **HX)), ["Wool Jacket", "Linen Shirt"])
        self.assertEqual(self.names(self.client.get(url, {"sort": "co2e_asc"}, **HX)), ["Linen Shirt", "Wool Jacket"])
        self.assertEqual(self.names(self.client.get(url, {"sort": "name"}, **HX)), ["Linen Shirt", "Wool Jacket"])
        self.assertEqual(self.names(self.client.get(url, {"sort": "newest"}, **HX)), ["Wool Jacket", "Linen Shirt"])

    def test_list_never_shows_other_users_items(self):
        resp = self.client.get(reverse("carbon_footprint:list"), {"q": "Secret"}, **HX)
        self.assertEqual(self.names(resp), [])
        self.assertContains(resp, "No estimate matches this search")

    def test_bar_is_relative_to_largest_visible_item(self):
        resp = self.client.get(reverse("carbon_footprint:list"), {"sort": "co2e_desc"}, **HX)
        self.assertEqual([e.bar_pct for e in resp.context["estimates"]], [100, 38])   # 1.5 / 4.0

    # ----- hapus -----

    def test_htmx_delete_returns_rows_and_toast(self):
        url = reverse("carbon_footprint:delete", args=[self.jacket.pk])
        resp = self.client.post(url, **HX)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(CarbonEstimate.objects.filter(pk=self.jacket.pk).exists())
        self.assertTemplateUsed(resp, "carbon_footprint/_rows.html")
        self.assertEqual(json.loads(resp["HX-Trigger"]), {"cf:toast": {"message": "Wool Jacket removed."}})
        self.assertNotContains(resp, "Wool Jacket")
        self.assertContains(resp, "Linen Shirt")

    def test_htmx_delete_keeps_active_filters(self):
        url = reverse("carbon_footprint:delete", args=[self.jacket.pk])
        resp = self.client.post(url, {"material": "cotton"}, **HX)
        self.assertEqual(self.names(resp), ["Linen Shirt"])

    def test_htmx_delete_other_users_item_is_404(self):
        resp = self.client.post(reverse("carbon_footprint:delete", args=[self.theirs.pk]), **HX)
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(CarbonEstimate.objects.filter(pk=self.theirs.pk).exists())

    def test_plain_delete_still_redirects_with_message(self):
        resp = self.client.post(reverse("carbon_footprint:delete", args=[self.jacket.pk]))
        self.assertRedirects(resp, reverse("carbon_footprint:list"))
        self.assertNotIn("HX-Trigger", resp)

    def test_htmx_delete_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("carbon_footprint:delete", args=[self.jacket.pk]), **HX)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CarbonEstimate.objects.filter(pk=self.jacket.pk).exists())

    # ----- Numbers -----

    def test_index_full_page_and_partial(self):
        url = reverse("carbon_footprint:index")
        self.assertTemplateUsed(self.client.get(url), "carbon_footprint/index.html")
        resp = self.client.get(url, **HX)
        self.assertTemplateUsed(resp, "carbon_footprint/_numbers.html")
        self.assertTemplateNotUsed(resp, "carbon_footprint/index.html")
        self.assertIn("HX-Request", resp["Vary"])

    def test_index_item_picker_switches_item(self):
        url = reverse("carbon_footprint:index")
        resp = self.client.get(url, {"item": self.shirt.pk}, **HX)
        self.assertEqual(resp.context["item"], self.shirt)
        self.assertEqual([i["name"] for i in resp.context["items"]], ["Wool Jacket", "Linen Shirt"])

    def test_index_ignores_other_users_item_id(self):
        resp = self.client.get(reverse("carbon_footprint:index"), {"item": self.theirs.pk}, **HX)
        self.assertNotEqual(resp.context["item"].user, self.other)
        self.assertNotContains(resp, "Secret Dress")

    # ----- pratinjau -----

    def test_preview_is_post_only(self):
        self.assertEqual(self.client.get(reverse("carbon_footprint:preview")).status_code, 405)

    def test_preview_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("carbon_footprint:preview"), FORM)
        self.assertEqual(resp.status_code, 302)

    def test_preview_computes_offline_without_saving(self):
        with mock.patch("requests.post", side_effect=AssertionError("pratinjau tidak boleh memanggil jaringan")):
            resp = self.client.post(reverse("carbon_footprint:preview"), {**FORM, "weight_kg": "1"})
        self.assertEqual(resp.status_code, 200)
        p = resp.context["p"]
        self.assertAlmostEqual(p["co2e"], float(fallback_co2e("cotton", 1)), places=1)
        self.assertEqual(p["cost_per_wear"], 12500)                 # 300000 / 24
        self.assertEqual(CarbonEstimate.objects.filter(name=FORM["name"]).count(), 0)

    def test_preview_uses_category_weight_when_weight_blank(self):
        resp = self.client.post(reverse("carbon_footprint:preview"), FORM)
        self.assertEqual(resp.context["p"]["weight"], Decimal(str(services.category_weight("shirt"))))

    def test_preview_without_price_has_no_cost_per_wear(self):
        resp = self.client.post(reverse("carbon_footprint:preview"), {**FORM, "price": ""})
        self.assertIsNone(resp.context["p"]["cost_per_wear"])

    def test_preview_with_incomplete_or_bad_input_shows_hint(self):
        url = reverse("carbon_footprint:preview")
        for data in (
            {},
            {**FORM, "material": ""},
            {**FORM, "category": "spaceship"},
            {**FORM, "weight_kg": "abc"},
            {**FORM, "weight_kg": "-2"},
            {**FORM, "estimated_wears": "0"},
            {**FORM, "price": "-5"},
        ):
            resp = self.client.post(url, data)
            self.assertEqual(resp.status_code, 200, data)
            self.assertIsNone(resp.context["p"], data)
            self.assertContains(resp, "Choose a category and material")

    # ----- form -----

    def test_form_page_embeds_category_weights_for_placeholder(self):
        resp = self.client.get(reverse("carbon_footprint:create"))
        self.assertContains(resp, 'id="cf-weights"')
        self.assertContains(resp, 'hx-post="%s"' % reverse("carbon_footprint:preview"))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])   # supaya test cepat
class AnalyzerTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("zidan", password="pw")
        self.other = User.objects.create_user("budi", password="pw")
        self.analyst = User.objects.create_user("sari", password="pw")
        self.analyst.groups.add(Group.objects.get_or_create(name=ANALYZER_GROUP)[0])   # grup juga dibuat oleh migrasi worth_to_buy_analyzer
        self.urls = [reverse("carbon_footprint:analyzer"), reverse("carbon_footprint:factors")]

    def make(self, user, material="cotton", category="shirt", co2e="3.2", wears=24, source="fallback", weight="0.25"):
        return CarbonEstimate.objects.create(
            user=user, name=f"{material} item", category=category, material=material,
            weight_kg=Decimal(weight), co2e_kg=Decimal(co2e), estimated_wears=wears, source=source,
        )

    # --- akses ---
    def test_anonymous_is_redirected_to_login(self):
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_regular_user_gets_403(self):
        self.client.force_login(self.user)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.urls[1], {"reset": "1"}).status_code, 403)

    def test_analyzer_and_superuser_allowed(self):
        admin = User.objects.create_superuser("root", password="pw")
        for user in (self.analyst, admin):
            self.assertTrue(can_open_analyzer(user))
            self.client.force_login(user)
            for url in self.urls:
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(is_analyzer(self.analyst))
        self.assertFalse(is_analyzer(self.user))           # definisi bersama: superuser bukan "akun Analyzer"
        self.assertFalse(can_open_analyzer(self.user))

    def test_staff_without_role_gets_403(self):
        staff = User.objects.create_user("staf", password="pw", is_staff=True)
        self.client.force_login(staff)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_analyzer_account_is_kept_out_of_personal_pages(self):
        """Sama seperti Worth to Buy: akun Analyzer memakai ruang Analyzer, bukan halaman pribadi user."""
        mine = self.make(self.user)
        self.client.force_login(self.analyst)
        for name, args in (("index", []), ("list", []), ("create", []), ("update", [mine.pk]), ("delete", [mine.pk])):
            self.assertEqual(self.client.get(reverse(f"carbon_footprint:{name}", args=args)).status_code, 403, name)
        self.assertEqual(self.client.post(reverse("carbon_footprint:preview"), FORM).status_code, 403)
        self.assertEqual(self.client.post(reverse("carbon_footprint:create"), FORM).status_code, 403)
        self.assertEqual(self.client.post(reverse("carbon_footprint:delete", args=[mine.pk])).status_code, 403)
        self.assertTrue(CarbonEstimate.objects.filter(pk=mine.pk).exists())

    def test_superuser_can_still_use_personal_pages(self):
        admin = User.objects.create_superuser("root", password="pw")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("carbon_footprint:index")).status_code, 200)

    def test_link_only_visible_to_superuser_on_personal_pages(self):
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse("carbon_footprint:index")), "Analyzer")
        admin = User.objects.create_superuser("root", password="pw")
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse("carbon_footprint:index")), "Analyzer")

    def test_pages_use_the_shared_analyzer_workspace(self):
        self.client.force_login(self.analyst)
        for url in self.urls:
            page = self.client.get(url)
            self.assertTemplateUsed(page, "worth_to_buy_analyzer/references/_layout.html")
            self.assertContains(page, "Menu Analyzer")                                         # sidebar bersama
            self.assertContains(page, reverse("worth_to_buy_analyzer:reference_list"))        # tautan ke Referensi pakaian
            self.assertContains(page, "Faktor emisi")
            self.assertContains(page, "wtb-page")
            self.assertContains(page, "Analisis karbon")

    def test_shared_sidebar_marks_only_the_current_carbon_page(self):
        self.client.force_login(self.analyst)
        page = self.client.get(self.urls[0]).content.decode()
        self.assertNotRegex(page, r'is-active"[^>]*href="%s"' % reverse("worth_to_buy_analyzer:reference_list"))

    # --- analisis ---
    def test_analysis_aggregates_all_users(self):
        self.make(self.user, "cotton", co2e="4.0", wears=20, source="climatiq")
        self.make(self.other, "cotton", co2e="2.0", wears=10)
        self.make(self.other, "wool", category="jacket", co2e="9.0", wears=30)
        a = build_analysis()
        self.assertEqual((a["total"], a["users"]), (3, 2))
        self.assertAlmostEqual(a["avg_co2e"], 5.0)
        self.assertEqual((a["climatiq_pct"], a["fallback_pct"]), (33, 67))
        by_material = {g["label"]: g for g in a["by_material"]}
        self.assertEqual(by_material["Cotton"]["count"], 2)
        self.assertAlmostEqual(by_material["Cotton"]["avg_co2e"], 3.0)
        self.assertEqual(a["by_material"][0]["label"], "Wool")          # rata-rata tertinggi di atas
        self.assertEqual((a["top"][0]["category_label"], a["top"][0]["material_label"]), ("Jacket", "Wool"))   # 9.0 / 30 wears = 0.30 per wear, tertinggi
        self.assertNotIn("name", a["top"][0])                           # tanpa nama item
        self.assertNotIn("user", a["top"][0])                           # tanpa pemilik
        self.assertEqual(a["score_low"] + a["score_mid"] + a["score_high"], 3)

    def test_analysis_empty_state(self):
        self.client.force_login(self.analyst)
        resp = self.client.get(self.urls[0])
        self.assertContains(resp, "Belum ada estimasi")

    def test_analyzer_page_renders_with_data(self):
        self.make(self.user)
        self.client.force_login(self.analyst)
        resp = self.client.get(self.urls[0])
        self.assertContains(resp, "Per bahan")
        self.assertContains(resp, "Emisi per pemakaian tertinggi")

    def test_analyzer_page_never_shows_private_names(self):
        CarbonEstimate.objects.create(user=self.user, name="Jaket Rahasia Zidan", category="shirt", material="cotton",
                                      weight_kg=Decimal("0.3"), co2e_kg=Decimal("3"))
        self.client.force_login(self.analyst)
        page = self.client.get(self.urls[0])
        self.assertContains(page, "Shirt")
        self.assertNotContains(page, "Jaket Rahasia")
        self.assertNotContains(page, "zidan")

    # --- faktor ---
    def factors_post(self, **overrides):
        data = {f"material_{k}": str(v) for k, v in FALLBACK_KG_CO2E_PER_KG.items()}
        data.update({f"category_{k}": str(v) for k, v in CATEGORY_WEIGHT_KG.items()})
        data.update({k: str(v) for k, v in overrides.items()})
        return data

    def test_defaults_used_when_tables_empty(self):
        self.assertEqual(services.material_rate("cotton"), FALLBACK_KG_CO2E_PER_KG["cotton"])
        self.assertEqual(services.category_weight("shirt"), CATEGORY_WEIGHT_KG["shirt"])

    def test_saving_only_stores_changed_values(self):
        self.client.force_login(self.analyst)
        resp = self.client.post(self.urls[1], self.factors_post(material_cotton="25.00"))
        self.assertRedirects(resp, self.urls[1])
        self.assertEqual(MaterialFactor.objects.count(), 1)
        row = MaterialFactor.objects.get()
        self.assertEqual((row.material, row.kg_co2e_per_kg, row.updated_by), ("cotton", Decimal("25.00"), self.analyst))

    def test_changed_factor_is_used_for_new_estimates(self):
        self.client.force_login(self.analyst)
        self.client.post(self.urls[1], self.factors_post(material_cotton="25.00", category_shirt="0.50"))
        co2e, source = services.compute_co2e("cotton", 1, None)
        self.assertEqual((co2e, source), (Decimal("25.00"), services.SOURCE_FALLBACK))
        self.client.force_login(self.user)                        # analyzer tidak memakai halaman pribadi
        self.client.post(reverse("carbon_footprint:create"), {**FORM, "price": "", "weight_kg": ""})
        obj = CarbonEstimate.objects.get()
        self.assertEqual(obj.weight_kg, Decimal("0.50"))          # berat kategori dari analyzer
        self.assertEqual(obj.co2e_kg, Decimal("12.50"))           # 0.50 kg x 25.00

    def test_value_back_to_default_removes_row(self):
        self.client.force_login(self.analyst)
        self.client.post(self.urls[1], self.factors_post(material_cotton="25.00"))
        self.client.post(self.urls[1], self.factors_post())
        self.assertEqual(MaterialFactor.objects.count(), 0)

    def test_invalid_values_are_rejected(self):
        self.client.force_login(self.analyst)
        for bad in ("0", "-3", "abc"):
            resp = self.client.post(self.urls[1], self.factors_post(material_cotton=bad))
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(MaterialFactor.objects.count(), 0)

    def test_recalculate_updates_only_offline_estimates(self):
        offline = self.make(self.user, "cotton", co2e="1.00", weight="2.00")
        online = self.make(self.user, "cotton", co2e="7.77", weight="2.00", source="climatiq")
        self.client.force_login(self.analyst)
        self.client.post(self.urls[1], {**self.factors_post(material_cotton="10.00"), "recalculate": "on"})
        offline.refresh_from_db(); online.refresh_from_db()
        self.assertEqual(offline.co2e_kg, Decimal("20.00"))      # 2 kg x 10
        self.assertEqual(online.co2e_kg, Decimal("7.77"))         # hasil Climatiq tidak disentuh

    def test_without_recalculate_existing_estimates_stay(self):
        offline = self.make(self.user, "cotton", co2e="1.00", weight="2.00")
        self.client.force_login(self.analyst)
        self.client.post(self.urls[1], self.factors_post(material_cotton="10.00"))
        offline.refresh_from_db()
        self.assertEqual(offline.co2e_kg, Decimal("1.00"))

    def test_messages_are_in_indonesian(self):
        self.client.force_login(self.analyst)
        resp = self.client.post(self.urls[1], {**self.factors_post(material_cotton="25.00"), "recalculate": "on"}, follow=True)
        self.assertContains(resp, "Faktor berhasil disimpan.")
        resp = self.client.post(self.urls[1], {"reset": "1"}, follow=True)
        self.assertContains(resp, "Faktor dikembalikan ke nilai bawaan.")

    def test_factor_changes_reach_worth_to_buy(self):
        """Satu tabel faktor untuk dua modul: perubahan Analyzer ikut ke snapshot karbon Worth to Buy."""
        from worth_to_buy_analyzer.models import PurchaseAnalysis
        from worth_to_buy_analyzer.services import refresh_carbon_snapshot

        self.client.force_login(self.analyst)
        self.client.post(self.urls[1], self.factors_post(material_cotton="10.00"))
        item = PurchaseAnalysis(clothing_name="Kemeja", material="cotton", weight_kg=Decimal("2.00"), price=Decimal("100000"))
        self.assertEqual(refresh_carbon_snapshot(item), "")
        self.assertEqual(item.carbon_kg_co2e, Decimal("20.0000"))     # 2 kg x 10.00, jalur offline

    def test_reset_restores_defaults(self):
        MaterialFactor.objects.create(material="wool", kg_co2e_per_kg=Decimal("99"))
        CategoryWeight.objects.create(category="jeans", weight_kg=Decimal("3"))
        self.client.force_login(self.analyst)
        self.client.post(self.urls[1], {"reset": "1"})
        self.assertEqual((MaterialFactor.objects.count(), CategoryWeight.objects.count()), (0, 0))
        self.assertEqual(services.material_rate("wool"), FALLBACK_KG_CO2E_PER_KG["wool"])

    # --- perintah setup ---
    def test_setup_analyzer_command(self):
        Group.objects.all().delete()
        call_command("setup_analyzer", "zidan", stdout=mock.Mock())
        self.assertTrue(is_analyzer(User.objects.get(username="zidan")))
        call_command("setup_analyzer", stdout=mock.Mock())          # aman dijalankan ulang
        with self.assertRaises(Exception):
            call_command("setup_analyzer", "tidak-ada", stdout=mock.Mock())
