from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .forms import PurchaseAnalysisForm
from .models import PurchaseAnalysis
from .services import analyze, refresh_carbon_snapshot


DATA = {
    "clothing_name": "Kemeja linen", "category": "top", "brand": "",
    "product_url": "", "existing_clothing": "none", "purpose": "routine",
    "price": "300000", "budget": "400000", "expected_wears": "60",
    "target_cpw": "10000", "wears_per_month": "4", "material": "", "weight_kg": "",
}
CARBON_DATA = {**DATA, "material": "cotton", "weight_kg": "0.50"}


def item(**overrides):
    values = {
        "clothing_name": "Kemeja", "category": "top", "existing_clothing": "none",
        "purpose": "routine", "price": Decimal("300000"), "budget": Decimal("400000"),
        "expected_wears": 60, "target_cpw": Decimal("10000"), "wears_per_month": Decimal("4"),
    }
    return PurchaseAnalysis(**(values | overrides))


class AnalysisRuleTests(SimpleTestCase):
    def test_cost_score_and_target_wears(self):
        result = analyze(item())
        self.assertEqual(result.cost_per_wear, Decimal("5000.00"))
        self.assertEqual(result.purchase_score, 100)
        self.assertEqual(result.wears_to_target, 30)
        self.assertEqual(result.months_to_target, 8)
        self.assertTrue(result.within_budget)
        self.assertTrue(result.meets_cpw_target)
        self.assertEqual(result.recommendation, "buy")
        self.assertIsNone(result.carbon_per_wear)

    def test_unrounded_cost_controls_target_comparison(self):
        result = analyze(item(price=Decimal("10.01"), expected_wears=3, target_cpw=Decimal("3.33")))
        self.assertEqual(result.cost_per_wear, Decimal("3.34"))
        self.assertFalse(result.meets_cpw_target)
        self.assertEqual(result.wears_to_target, 4)
        result = analyze(item(price=Decimal("1"), expected_wears=3, target_cpw=Decimal("0.33")))
        self.assertEqual(result.cost_per_wear, Decimal("0.33"))
        self.assertFalse(result.meets_cpw_target)

    def test_half_up_rounding(self):
        self.assertEqual(analyze(item(price=Decimal("10.01"), expected_wears=2)).cost_per_wear, Decimal("5.01"))

    def test_score_breakdown_with_partial_budget_and_target(self):
        result = analyze(item(target_cpw=Decimal("2500"), budget=Decimal("150000")))
        self.assertEqual(result.purchase_score, 65)  # 20 + 15 + 20 + 10
        self.assertEqual(result.recommendation, "postpone")

    def test_recommendation_priority(self):
        cases = [
            ({"existing_clothing": "usable", "budget": Decimal(0)}, "use_existing"),
            ({"existing_clothing": "repairable"}, "repair"),
            ({"purpose": "occasion"}, "borrow_rent"),
            ({"purpose": "variety"}, "postpone"),
            ({"target_cpw": Decimal("100")}, "alternative"),
            ({"purpose": "replacement"}, "buy"),
        ]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                self.assertEqual(analyze(item(**changes)).recommendation, expected)

    def test_budget_zero_missing_frequency_and_extreme_valid_inputs(self):
        result = analyze(item(budget=Decimal(0), wears_per_month=None))
        self.assertEqual(result.score_breakdown["budget"], 0)
        self.assertIsNone(result.months_to_target)
        result = analyze(item(price=Decimal("9999999999.99"), expected_wears=1, target_cpw=Decimal("0.01")))
        self.assertTrue(0 <= result.purchase_score <= 100)
        self.assertEqual(result.wears_to_target, 999999999999)

    def test_carbon_per_wear(self):
        result = analyze(item(carbon_kg_co2e=Decimal("4.69")))
        self.assertEqual(result.carbon_per_wear, Decimal("0.0782"))


class FormValidationTests(SimpleTestCase):
    def test_rejects_invalid_values(self):
        cases = {
            "price": ["0", "-1", "NaN", "Infinity", "10000000000", "1.001"],
            "budget": ["-1", "NaN"], "expected_wears": ["0", "-1", "1.5", "2147483648"],
            "target_cpw": ["0", "-1"], "wears_per_month": ["0", "-1"],
            "category": ["made-up"], "purpose": ["made-up"], "existing_clothing": ["made-up"],
            "clothing_name": ["", " "], "product_url": ["javascript:alert(1)", "ftp://example.com/file"],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    form = PurchaseAnalysisForm({**DATA, field: value})
                    self.assertFalse(form.is_valid())
                    self.assertIn(field, form.errors)

    def test_zero_budget_and_optional_fields_are_valid(self):
        form = PurchaseAnalysisForm({**DATA, "budget": "0", "wears_per_month": ""})
        self.assertTrue(form.is_valid(), form.errors)

    def test_material_and_weight_must_be_supplied_together(self):
        for changes, field in [({"material": "cotton"}, "weight_kg"), ({"weight_kg": "0.5"}, "material"),
                               ({"material": "cotton", "weight_kg": "0"}, "weight_kg")]:
            with self.subTest(changes=changes):
                form = PurchaseAnalysisForm(DATA | changes)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)


@override_settings(CLIMATIQ_API_KEY="")
class CarbonAdapterTests(SimpleTestCase):
    def test_missing_material_never_calls_service(self):
        obj = item()
        with patch("worth_to_buy_analyzer.services.compute_co2e") as compute:
            self.assertEqual(refresh_carbon_snapshot(obj), "")
        compute.assert_not_called()
        self.assertIsNone(obj.carbon_kg_co2e)

    def test_real_offline_service_and_provenance(self):
        obj = item(material="cotton", weight_kg=Decimal("0.50"))
        self.assertEqual(refresh_carbon_snapshot(obj), "")
        self.assertEqual(obj.carbon_kg_co2e, Decimal("9.0600"))
        self.assertEqual(obj.carbon_source, "fallback")
        self.assertIn("18.12", obj.carbon_reference)
        self.assertIn("bukan respons API", obj.carbon_scope)
        self.assertIsNotNone(obj.carbon_estimated_at)

    @override_settings(CLIMATIQ_API_KEY="test-only")
    def test_climatiq_path_uses_existing_service(self):
        obj = item(material="cotton", weight_kg=Decimal("0.50"))
        with patch("carbon_footprint.services.estimate_money_co2e", return_value=4.69):
            self.assertEqual(refresh_carbon_snapshot(obj), "")
        self.assertEqual(obj.carbon_kg_co2e, Decimal("4.6900"))
        self.assertEqual(obj.carbon_source, "climatiq")
        self.assertIn("CEDA 2025", obj.carbon_reference)

    def test_bad_service_values_clear_old_snapshot(self):
        for amount, source in [("NaN", "climatiq"), ("Infinity", "climatiq"),
                               ("-1", "fallback"), ("0", "fallback"),
                               ("0.000001", "fallback"), ("1e20", "climatiq"), ("2", "unknown")]:
            with self.subTest(amount=amount, source=source):
                obj = item(material="cotton", weight_kg=Decimal("0.5"), carbon_kg_co2e=Decimal("3"))
                with patch("worth_to_buy_analyzer.services.compute_co2e", return_value=(amount, source)):
                    self.assertTrue(refresh_carbon_snapshot(obj))
                self.assertIsNone(obj.carbon_kg_co2e)
                self.assertEqual(obj.carbon_reference, "")
                self.assertIsNone(obj.carbon_estimated_at)


@override_settings(CLIMATIQ_API_KEY="", PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AnalyzerFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("lica", password="test-password")
        cls.other = get_user_model().objects.create_user("other", password="test-password")

    def setUp(self):
        self.client.force_login(self.user)

    def url(self, name, obj=None):
        return reverse(f"worth_to_buy_analyzer:{name}", args=[obj.pk] if obj else None)

    def saved_item(self, **changes):
        obj = item(owner=self.user, **changes)
        obj.save()
        return obj

    def test_real_login_page_and_next_redirect(self):
        self.client.logout()
        target = self.url("create")
        response = self.client.get(target)
        self.assertRedirects(response, f"{reverse('main:login')}?next={target}")
        response = self.client.post(f"{reverse('main:login')}?next={target}", {"username": "lica", "password": "test-password"})
        self.assertRedirects(response, target)
        response = self.client.post(reverse("main:logout"))
        self.assertRedirects(response, reverse("main:login"))

    def test_login_rejects_external_redirect(self):
        for next_url in ("https://example.com/", "//example.com/", "javascript:alert(1)"):
            with self.subTest(next_url=next_url):
                self.client.logout()
                response = self.client.post(reverse("main:login"), {
                    "username": "lica", "password": "test-password", "next": next_url,
                })
                self.assertRedirects(response, reverse("main:show_main"))

    def test_login_rejects_external_next_from_query_string(self):
        self.client.logout()
        response = self.client.post(reverse("main:login") + "?next=https://example.com/", {
            "username": "lica", "password": "test-password",
        })
        self.assertRedirects(response, reverse("main:show_main"))

    def test_anonymous_requests_cannot_read_or_mutate(self):
        obj = self.saved_item()
        self.client.logout()
        urls = [self.url("analyzer"), self.url("create")]
        urls += [self.url(name, obj) for name in ("detail", "update", "delete", "decide", "refresh_carbon")]
        for url in urls:
            for method in (self.client.get, self.client.post):
                with self.subTest(url=url, method=method.__name__):
                    self.assertEqual(method(url).status_code, 302)
        self.assertEqual(PurchaseAnalysis.objects.count(), 1)

    def test_create_ignores_spoofed_owner_carbon_and_decision(self):
        response = self.client.post(self.url("create"), {
            **DATA, "owner": self.other.pk, "carbon_kg_co2e": "999", "carbon_source": "climatiq",
            "rule_version": "999", "decision": "buy", "purchase_score": "100",
        })
        obj = PurchaseAnalysis.objects.get()
        self.assertRedirects(response, self.url("detail", obj))
        self.assertEqual(obj.owner, self.user)
        self.assertIsNone(obj.carbon_kg_co2e)
        self.assertEqual(obj.carbon_source, "")
        self.assertEqual(obj.rule_version, 1)
        self.assertEqual(obj.decision, "undecided")
        result_page = self.client.get(self.url("detail", obj))
        self.assertEqual(result_page.context["result"].cost_per_wear, Decimal("5000.00"))
        self.assertContains(result_page, "Data karbon belum tersedia")
        self.client.get(response.url)
        self.assertEqual(PurchaseAnalysis.objects.count(), 1)

    def test_empty_post_and_invalid_update_preserve_database(self):
        response = self.client.post(self.url("create"), {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].is_bound)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(PurchaseAnalysis.objects.exists())
        obj = self.saved_item()
        response = self.client.post(self.url("update", obj), {**DATA, "price": "-1"})
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.price, Decimal("300000"))

    def test_history_is_private_and_paginated(self):
        for i in range(11):
            self.saved_item(clothing_name=f"Pakaian {i}")
        other_item = item(owner=self.other, clothing_name="Private item")
        other_item.save()
        response = self.client.get(self.url("analyzer"))
        self.assertEqual(response.context["page_obj"].paginator.count, 11)
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertNotContains(response, "Private item")
        self.assertEqual(len(self.client.get(self.url("analyzer"), {"page": 2}).context["page_obj"]), 1)
        self.assertEqual(self.client.get(self.url("analyzer"), {"page": "bad"}).status_code, 200)

    def test_other_user_cannot_access_any_object_endpoint(self):
        obj = item(owner=self.other)
        obj.save()
        for name in ("detail", "update", "delete"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(self.url(name, obj)).status_code, 404)
        for name in ("update", "delete", "decide", "refresh_carbon"):
            with self.subTest(name=name):
                self.assertEqual(self.client.post(self.url(name, obj), DATA).status_code, 404)
        obj.refresh_from_db()
        self.assertEqual(obj.owner, self.other)
        self.assertEqual(obj.clothing_name, "Kemeja")

    def test_update_recalculates_result_and_resets_old_decision(self):
        obj = self.saved_item()
        self.client.post(self.url("decide", obj), {"decision": "buy", "decision_note": "Untuk kerja"})
        response = self.client.post(self.url("update", obj), {**DATA, "expected_wears": "10", "owner": self.other.pk})
        self.assertRedirects(response, self.url("detail", obj))
        obj.refresh_from_db()
        self.assertEqual(analyze(obj).cost_per_wear, Decimal("30000"))
        self.assertEqual(obj.owner, self.user)
        self.assertEqual(obj.decision, "undecided")
        self.assertEqual(obj.decision_note, "Untuk kerja")
        self.assertIsNone(obj.decided_at)

    def test_decision_timestamp_and_validation(self):
        obj = self.saved_item()
        url = self.url("decide", obj)
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, {"decision": "invalid"})
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.decision, "undecided")
        self.client.post(url, {"decision": "buy", "decision_note": "Budget cukup"})
        obj.refresh_from_db()
        timestamp = obj.decided_at
        self.assertIsNotNone(timestamp)
        self.client.post(url, {"decision": "buy", "decision_note": "Catatan baru"})
        obj.refresh_from_db()
        self.assertEqual(obj.decided_at, timestamp)
        self.assertEqual(obj.decision_note, "Catatan baru")
        self.client.post(url, {"decision": "undecided"})
        obj.refresh_from_db()
        self.assertIsNone(obj.decided_at)

    def test_delete_requires_confirmation_post(self):
        obj = self.saved_item()
        url = self.url("delete", obj)
        self.assertContains(self.client.get(url), "Hapus analisis?")
        self.assertTrue(PurchaseAnalysis.objects.filter(pk=obj.pk).exists())
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertRedirects(self.client.post(url), self.url("analyzer"))
        self.assertFalse(PurchaseAnalysis.objects.filter(pk=obj.pk).exists())

    def test_deletePOST(self):
        obj = self.saved_item()
        self.assertRedirects(self.client.post(self.url("delete", obj)), self.url("analyzer"))
        self.assertFalse(PurchaseAnalysis.objects.filter(pk=obj.pk).exists())

    def test_deleteGET(self):
        obj = self.saved_item()
        self.assertContains(self.client.get(self.url("delete", obj)), "Hapus analisis?")
        self.assertTrue(PurchaseAnalysis.objects.filter(pk=obj.pk).exists())

    def test_csrf_required_on_every_mutation(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        obj = self.saved_item()
        urls = [self.url("create")] + [self.url(name, obj) for name in ("update", "delete", "decide", "refresh_carbon")]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(client.post(url, DATA).status_code, 403)
        self.assertEqual(PurchaseAnalysis.objects.count(), 1)
        response = client.get(self.url("create"))
        token = client.cookies["csrftoken"].value
        response = client.post(self.url("create"), {**DATA, "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PurchaseAnalysis.objects.count(), 2)

    def test_html_is_escaped_in_result_and_history(self):
        obj = self.saved_item(clothing_name='<script>alert("x")</script>')
        for name in ("detail", "analyzer"):
            response = self.client.get(self.url(name, obj if name == "detail" else None))
            self.assertNotContains(response, '<script>alert("x")</script>')
            self.assertContains(response, "&lt;script&gt;")

    def test_carbon_recomputed_only_for_relevant_inputs(self):
        with patch("worth_to_buy_analyzer.services.compute_co2e", return_value=(Decimal("4.69"), "climatiq")) as compute:
            self.client.post(self.url("create"), CARBON_DATA)
            obj = PurchaseAnalysis.objects.get()
            self.assertEqual(compute.call_count, 1)
            response = self.client.get(self.url("detail", obj))
            self.assertContains(response, "CEDA 2025")
            self.client.post(self.url("update", obj), {**CARBON_DATA, "expected_wears": "30"})
            self.assertEqual(compute.call_count, 1)
            self.client.post(self.url("update", obj), {**CARBON_DATA, "price": "350000"})
            self.assertEqual(compute.call_count, 2)
            self.client.post(self.url("update", obj), DATA)
            self.assertEqual(compute.call_count, 2)
        obj.refresh_from_db()
        self.assertIsNone(obj.carbon_kg_co2e)
        self.assertEqual(obj.carbon_source, "")
        self.assertIsNone(obj.carbon_estimated_at)

    def test_carbon_failure_still_saves_and_can_retry(self):
        with patch("worth_to_buy_analyzer.services.compute_co2e", side_effect=ValueError("bad upstream response")):
            response = self.client.post(self.url("create"), CARBON_DATA, follow=True)
        self.assertContains(response, "estimasi karbon belum tersedia")
        obj = PurchaseAnalysis.objects.get()
        self.assertIsNone(obj.carbon_kg_co2e)
        self.assertEqual(self.client.get(self.url("refresh_carbon", obj)).status_code, 405)
        with patch("worth_to_buy_analyzer.services.compute_co2e", return_value=(Decimal("9.06"), "fallback")):
            self.client.post(self.url("refresh_carbon", obj))
        obj.refresh_from_db()
        self.assertEqual(obj.carbon_kg_co2e, Decimal("9.0600"))
        self.assertEqual(obj.carbon_source, "fallback")

    def test_failed_recompute_does_not_keep_old_emissions(self):
        self.client.post(self.url("create"), CARBON_DATA)
        obj = PurchaseAnalysis.objects.get()
        self.assertIsNotNone(obj.carbon_kg_co2e)
        with patch("worth_to_buy_analyzer.services.compute_co2e", side_effect=ValueError("bad response")):
            self.client.post(self.url("update", obj), {**CARBON_DATA, "price": "500000"})
        obj.refresh_from_db()
        self.assertEqual(obj.price, Decimal("500000"))
        self.assertIsNone(obj.carbon_kg_co2e)
        self.assertIsNone(obj.carbon_estimated_at)

    def test_note_length_and_unchanged_edit(self):
        obj = self.saved_item(clothing_name=DATA["clothing_name"])
        url = self.url("decide", obj)
        response = self.client.post(url, {"decision": "buy", "decision_note": "x" * 1001})
        self.assertTrue(response.context["decision_form"].errors)
        self.client.post(url, {"decision": "buy", "decision_note": "Tetap disimpan"})
        obj.refresh_from_db()
        timestamp = obj.decided_at
        self.client.post(self.url("update", obj), DATA)
        obj.refresh_from_db()
        self.assertEqual(obj.decision, "buy")
        self.assertEqual(obj.decision_note, "Tetap disimpan")
        self.assertEqual(obj.decided_at, timestamp)
