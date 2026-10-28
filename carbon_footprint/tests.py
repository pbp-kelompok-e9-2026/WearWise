from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
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
from .models import CarbonEstimate

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

    API key dikosongkan walau environment memilikinya, dan setiap panggilan
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