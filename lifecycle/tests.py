from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from wardrobe.models import ClothingItem

from .models import ConditionRecord
from .services import recommend


class RecommendTest(TestCase):
    def test_good_menjadi_reuse(self):
        self.assertEqual(recommend("good"), "reuse")

    def test_minor_dan_major_menjadi_repair(self):
        self.assertEqual(recommend("minor"), "repair")
        self.assertEqual(recommend("major"), "repair")

    def test_worn_out_menjadi_recycle(self):
        self.assertEqual(recommend("worn_out"), "recycle")

    def test_kondisi_tidak_dikenal_menjadi_repair(self):
        self.assertEqual(recommend("aneh"), "repair")


class LifecycleViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="airell", password="pass12345")
        self.other = User.objects.create_user(username="lain", password="pass12345")
        self.item = ClothingItem.objects.create(
            user=self.user, name="Kemeja Linen", category="TOP",
            material="linen", price=150000, purchase_date=date(2026, 1, 10),
        )
        self.other_item = ClothingItem.objects.create(
            user=self.other, name="Jaket Lain", category="OUTER",
            material="cotton", price=200000, purchase_date=date(2026, 1, 10),
        )
        self.record = ConditionRecord.objects.create(
            user=self.user, item=self.item, condition="minor", recommendation="repair",
        )
        self.client.login(username="airell", password="pass12345")

    def test_str_model(self):
        self.assertEqual(str(self.record), "Kemeja Linen - Rusak ringan")

    def test_belum_login_dialihkan_ke_login(self):
        self.client.logout()
        response = self.client.get(reverse("lifecycle:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("main:login"), response.url)

    def test_list_hanya_menampilkan_milik_sendiri(self):
        ConditionRecord.objects.create(user=self.other, item=self.other_item, condition="good")
        response = self.client.get(reverse("lifecycle:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["records"]), [self.record])

    def test_filter_rekomendasi(self):
        ConditionRecord.objects.create(user=self.user, item=self.item, condition="good", recommendation="reuse")
        response = self.client.get(reverse("lifecycle:index"), {"recommendation": "reuse"})
        records = list(response.context["records"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].recommendation, "reuse")

    def test_filter_status(self):
        response = self.client.get(reverse("lifecycle:index"), {"status": "done"})
        self.assertEqual(list(response.context["records"]), [])

    def test_halaman_create_dropdown_hanya_baju_sendiri(self):
        response = self.client.get(reverse("lifecycle:create"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["form"].fields["item"].queryset), [self.item])

    def test_create_mengisi_user_dan_rekomendasi(self):
        response = self.client.post(reverse("lifecycle:create"), {
            "item": self.item.pk, "condition": "worn_out", "status": "pending",
        })
        self.assertRedirects(response, reverse("lifecycle:index"))
        record = ConditionRecord.objects.get(condition="worn_out")
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.recommendation, "recycle")

    def test_create_tidak_valid_tanpa_kondisi(self):
        response = self.client.post(reverse("lifecycle:create"), {"item": self.item.pk, "status": "pending"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_create_tidak_bisa_pakai_baju_orang_lain(self):
        self.client.post(reverse("lifecycle:create"), {
            "item": self.other_item.pk, "condition": "good", "status": "pending",
        })
        self.assertFalse(ConditionRecord.objects.filter(item=self.other_item).exists())

    def test_update_menghitung_ulang_rekomendasi(self):
        url = reverse("lifecycle:update", args=[self.record.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {"item": self.item.pk, "condition": "good", "status": "done"})
        self.assertRedirects(response, reverse("lifecycle:index"))
        self.record.refresh_from_db()
        self.assertEqual(self.record.recommendation, "reuse")
        self.assertEqual(self.record.status, "done")

    def test_delete_get_hanya_konfirmasi(self):
        response = self.client.get(reverse("lifecycle:delete", args=[self.record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ConditionRecord.objects.filter(pk=self.record.pk).exists())

    def test_delete_post_menghapus(self):
        response = self.client.post(reverse("lifecycle:delete", args=[self.record.pk]))
        self.assertRedirects(response, reverse("lifecycle:index"))
        self.assertFalse(ConditionRecord.objects.filter(pk=self.record.pk).exists())

    def test_user_lain_tidak_bisa_edit_atau_hapus(self):
        self.client.logout()
        self.client.login(username="lain", password="pass12345")
        self.assertEqual(self.client.get(reverse("lifecycle:update", args=[self.record.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("lifecycle:delete", args=[self.record.pk])).status_code, 404)
        self.assertTrue(ConditionRecord.objects.filter(pk=self.record.pk).exists())

    def test_json_hanya_milik_sendiri(self):
        ConditionRecord.objects.create(user=self.other, item=self.other_item, condition="good")
        response = self.client.get(reverse("lifecycle:json"))
        data = response.json()["records"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["item"], "Kemeja Linen")
        self.assertEqual(data[0]["condition_display"], "Rusak ringan")