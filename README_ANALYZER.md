#### Peran Analyzer (modul Carbon Footprint)

Peran Analyzer dipakai bersama modul Worth to Buy. Definisinya hanya ada di `worth_to_buy_analyzer/roles.py`
(grup `Analyzer`, `is_analyzer`, `analyzer_required`, `purchase_user_required`) dan `carbon_footprint/access.py` memakainya ulang.
Cara memberi role: Django admin, Users, Groups, pilih `Analyzer` (panduan lengkap ada di `worth_to_buy_analyzer/ANALYZER_ROLE.md`).
Grup dibuat oleh migrasi `worth_to_buy_analyzer.0005`, jadi `setup_analyzer` hanya jalan pintas opsional untuk lingkungan lokal.

| Path | Nama | Fungsi |
|---|---|---|
| `/carbon/analyzer/` | `carbon_footprint:analyzer` | Analisis gabungan semua data: ringkasan, per bahan dan kategori, sebaran skor, 10 kombinasi kategori + bahan dengan emisi per pemakaian tertinggi |
| `/carbon/analyzer/factors/` | `carbon_footprint:factors` | Atur faktor emisi per bahan dan berat per kategori |

Aturan akses (sama dengan Worth to Buy):
- Ruang Analyzer: akun di grup `Analyzer` atau superuser. User biasa dan staff tanpa role mendapat 403, yang belum login diarahkan ke login.
- Halaman pribadi (`/carbon/`, `/carbon/estimates/...`): akun Analyzer mendapat 403. User biasa dan superuser boleh.
- Analisis hanya menampilkan angka gabungan. Nama user dan nama item tidak ditampilkan.

Catatan teknis:
- Nilai yang diubah Analyzer disimpan di `MaterialFactor` dan `CategoryWeight` beserta akun pengubahnya. Tabel hanya berisi nilai yang berbeda dari bawaan `constants.py`.
- `compute_co2e` membaca tabel itu, jadi perubahan faktor juga berlaku untuk snapshot karbon di Worth to Buy. Akibatnya tes yang memanggil `compute_co2e` harus memakai `TestCase`, bukan `SimpleTestCase`.
- Opsi "Hitung ulang" memperbarui estimasi offline yang sudah ada. Hasil Climatiq tidak diubah.
- Halaman Analyzer memakai `worth_to_buy_analyzer/references/_layout.html` (sidebar, topbar, CSS ruang Analyzer). Tautan "Analisis karbon" dan "Faktor emisi" di sidebar itu muncul otomatis bila modul karbon terpasang.
