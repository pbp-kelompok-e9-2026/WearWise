## Daftar Modul Rencana

### 1. Wardrobe Management

**Penanggung jawab:** Ali Jundi Qowi (2506611585)

- **Create:** Menambahkan pakaian baru ke wardrobe (nama, kategori, material, harga, tanggal beli, foto)
- **Read:** Melihat daftar dan detail pakaian, termasuk jumlah pemakaian
- **Update:** Mengubah data pakaian dan menambah jumlah pemakaian
- **Delete:** Menghapus pakaian dari wardrobe

### 2. Worth to Buy Analyzer

**Penanggung jawab:** Khalishah Nafisah (2506605840)

- **Create:** Menginput calon barang beserta harga, material, dan estimasi frequency of use, lalu menghitung cost per wear dan purchase score
- **Read:** Melihat hasil analisis dan riwayat pengecekan calon barang
- **Update:** Mengubah data input atau estimasi pemakaian untuk menghitung ulang purchase score
- **Delete:** Menghapus calon barang dan hasil analisisnya
- **Role Analyzer:** Mengelola database referensi pakaian melalui ruang khusus
  setelah login: tambah, lihat, edit, hapus, serta simpan sebagai draft atau
  terbitkan ke katalog user. Referensi terbit dapat digunakan sebagai isian awal
  analisis pribadi user.

### 3. Carbon Footprint & Sustainability

**Penanggung jawab:** Zidan Fauzan Ikrar (2506589616)

- **Create:** Membuat estimasi carbon footprint pakaian berdasarkan material dan kategori
- **Read:** Melihat hasil estimasi, sustainability score, dan comparison antar pakaian atau material
- **Update:** Mengubah material atau kategori untuk menghitung ulang estimasi dan sustainability score
- **Delete:** Menghapus data estimasi carbon footprint

### 4. Repair & Clothing Lifecycle

**Penanggung jawab:** Raden Stanislaus Airell Prakosa Sinaga (2506657251)

- **Create:** Mencatat kondisi pakaian dan membuat rekomendasi repair, reuse, atau recycle
- **Read:** Melihat riwayat kondisi pakaian, rekomendasi, dan repair guide
- **Update:** Memperbarui kondisi pakaian dan status tindak lanjut rekomendasi
- **Delete:** Menghapus catatan kondisi dan rekomendasi

### 5. Dashboard, Profile, & Eco Challenge

**Penanggung jawab:** Brigitta Elissa Rebecca Simanjuntak (2506601855)

- **Create:** Menginput data ke database untuk dianalisis dan mengikuti eco challenge baru
- **Read:** Melihat statistik wardrobe, money saved, carbon saved, progres eco challenge, dan profile
- **Update:** Mengubah data profile, progres eco challenge, dan data database yang sudah diinput
- **Delete:** Menghapus data database yang tidak diperlukan dan keluar dari eco challenge

## AI Disclosure

### Worth to Buy Analyzer

Bantuan AI digunakan untuk memperbaiki sebagian kode modul Worth to Buy Analyzer yang kurang tepat dan membantu memahami konsep integrasi Tailwind v4, serta pengujian. Perubahan diverifikasi melalui pengujian otomatis dan pengecekan antarmuka. Penanggung jawab modul tetap perlu meninjau, memahami, dan memvalidasi hasil sebelum menggabungkannya ke proyek kelompok.

## Public API / Mock API

- [Climatiq](https://www.climatiq.io/docs/api-reference)

## Tautan Deployment PWS

- [PWS](https://zidan-fauzan-wearwise.pws.cs.ui.ac.id)

## Design Plan

- [Figma](https://www.figma.com/design/PVHrNdTOolsl7Ke1kR2Fv8/Untitled?node-id=0-1&p=f&t=FQ7cldO460FBvFS6-0)

## Peran Pengguna

### 1. User
- Input pakaian yang ingin dibeli
- Cek Worth-to-Buy Score
- Cek Carbon Footprint
- Mendapat rekomendasi life cycle pakaian
- Menyimpan wardrobe

### 2. Analyzer
- Akun khusus untuk mengelola referensi pakaian, berbeda dari user yang melakukan analisis pribadi.
- Mengisi identitas, harga, bahan/berat, dan sumber referensi; mengelola draft serta publikasi.
- Role diberikan admin melalui grup `Analyzer`, bukan dipilih saat registrasi.
- Setelah login diarahkan ke `/worth-to-buy/workspace/`.

### 3. Admin
- Mengelola data user
- Monitor perilaku user atau problem


## Dokumentasi
### Modul 1: Wardrobe Management ('wardrobe')

Bertanggungjawab menyimpan, meneglompokkan, dan mengelola koleksi pakaian digital milik pengguna yang sudah login. 

#### Fitur
- CRUD Pakaian Berbasis AJAX: Tambah item baru pakai modal popover serta hapus item yang dilakukan secara asinkronus

- Kalkulasi Cost Per Wear: hitung otomatis rasio kehematan pakaian tiap user menambah jumlah pemakaian
CPW  = Harga Beli / Jumlah Pemakaian

- Filter Kategori Dinamis: Mengambil dan menyaring daftar pakaian berdasarkan kategori secara real-time menggunakan query parameter JSON

- Isolasi data: setiap entri pakaian hanya bisa diakses oleh pemiliknya sendiri, menggunakan @login_required

#### Model 'ClothingItem'
`id (UUID)`, `user (ForeignKey)`, `name`, `category`, `material`, `price`, `purchase_date`, `image`, `image_url`, `wear_count (default 0)`, `created_at`, `updated_at`

#### URL
| Path | Nama | Fungsi |
|---|---|---|
|/wardrobe/|	wardrobe:index	
Halaman utama| digital wardrobe|

|/wardrobe/json/|	wardrobe:get_clothing_json	|
Ambil data pakaian JSON (dukungan filter ?category=) |

|/wardrobe/add-ajax/|	wardrobe:add_clothing_ajax|	
Tambah pakaian baru via AJAX|

|/wardrobe/increment-wear/<id>/|	wardrobe:increment_wear	|
Tambah frekuensi pemakaian (+1) via AJAX|

|/wardrobe/delete-ajax/<id>/	|wardrobe:delete_clothing_ajax|	
Hapus item pakaian via AJAX|

#### Konfigurasi
Daftarkan modul di `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'wardrobe',
]
```
Atur konfigurasi media file di `settings.py` untuk mendukung unggah foto pakaian:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```


Semua endpoint perlu otentikasi pengguna
#### Menjalankan
```bash
python manage.py makemigrations wardrobe
python manage.py migrate
python manage.py runserver
```
#### Pengujian
```bash
python manage.py test wardrobe
```
Test jalan mandiri agar semua fungsi pembuatan model, kalkulasi, kelancaran AJAX, serta keamanan berjalan sesuai yang diinginkan

## Modul 3: Carbon Footprint & Sustainability (`carbon_footprint`)

Menghitung estimasi jejak karbon (kg CO₂e) tiap pakaian, lalu menampilkan biaya per pemakaian dan skor keberlanjutan. Modul punya dua sisi: halaman pribadi untuk user biasa (halaman utamanya bernama **Numbers**) dan ruang **Analyzer** untuk analisis gabungan.

### 1. Fitur

| Sisi | Fitur |
|---|---|
| User | Numbers (angka satu item), daftar estimasi (cari, filter material, urutan), tambah, ubah, hapus, pratinjau saat mengisi form |
| Analyzer | Analisis gabungan seluruh data (anonim), pengaturan faktor emisi dan berat per kategori |

- Setiap estimasi hanya bisa diakses oleh pemiliknya. Data user selalu difilter per akun, jadi estimasi milik orang lain tidak bisa dibuka lewat URL.
- Halaman **Numbers** menampilkan estimasi terbaru: jumlah pemakaian, biaya per pemakaian, emisi CO₂e, dan skor keberlanjutan (0 sampai 100).

### 2. Perhitungan CO₂e

Perhitungan bersifat hybrid:

1. **Climatiq.** Jika harga diisi dan `CLIMATIQ_API_KEY` tersedia, emisi dihitung lewat [Climatiq](https://www.climatiq.io/) memakai faktor berbasis pengeluaran (spend-based) untuk Indonesia (CEDA 2025). Harga dalam rupiah dikonversi otomatis ke USD oleh Climatiq.
2. **Estimasi offline.** Tanpa harga atau tanpa API key, emisi dihitung dari **berat × faktor material**.
3. **Fallback otomatis.** Jika panggilan Climatiq gagal, aplikasi memakai cara kedua, jadi halaman tidak error.

Kolom `source` pada setiap estimasi menyimpan asal angkanya (`climatiq` atau `fallback`).

Faktor material dan berat bawaan kategori ada di `constants.py`. Nilai yang diubah Analyzer disimpan di tabel `MaterialFactor` dan `CategoryWeight`, dan nilai ini yang dipakai saat perhitungan karena faktor dibaca dari database.

#### Rumus

| Besaran | Rumus |
|---|---|
| Emisi (offline) | `berat_kg × faktor_material` (kg CO₂e per kg) |
| Biaya per pemakaian | `harga / estimasi_pemakaian` |
| Skor | `100 × (1 − (CO₂e / pemakaian) / 0,75)`, dibatasi 0 sampai 100 |

Angka 0,75 kg CO₂e per pemakaian adalah batas skor 0. Nilai ini dan semua faktor bawaan ada di `carbon_footprint/constants.py`. Skor dihitung oleh `services.sustainability_score`.

### 3. Model

**`CarbonEstimate`**: `user`, `name`, `category`, `material`, `weight_kg`, `price` (opsional), `estimated_wears` (default 30), `co2e_kg`, `source`, `created_at`, `updated_at`. Jika berat dikosongkan, dipakai berat rata-rata per kategori.

**`MaterialFactor`** dan **`CategoryWeight`**: menyimpan faktor emisi dan berat per kategori yang diubah Analyzer (menimpa nilai bawaan di `constants.py`).

### 4. URL

| Path | Nama | Akses |
|---|---|---|
| `/carbon/` | `carbon_footprint:index` (Numbers) | user biasa dan superuser |
| `/carbon/estimates/` | `carbon_footprint:list` | idem |
| `/carbon/estimates/new/` | `carbon_footprint:create` | idem |
| `/carbon/estimates/<id>/edit/` | `carbon_footprint:update` | idem |
| `/carbon/estimates/<id>/delete/` | `carbon_footprint:delete` (hanya POST) | idem |
| `/carbon/estimates/preview/` | `carbon_footprint:preview` (POST, HTMX) | idem |
| `/carbon/analyzer/` | `carbon_footprint:analyzer` | grup Analyzer atau superuser |
| `/carbon/analyzer/factors/` | `carbon_footprint:factors` | grup Analyzer atau superuser |

Semua halaman wajib login.

### 5. Peran Analyzer

Peran didefinisikan satu kali di `worth_to_buy_analyzer/roles.py` (grup `Analyzer`) dan dipakai bersama modul Worth to Buy. Grup dibuat oleh migrasi `worth_to_buy_analyzer.0005`. Cara memberi peran: Django admin, Users, Groups, pilih `Analyzer`.

- Akun Analyzer mendapat 403 di halaman pribadi.
- User biasa dan staff tanpa peran mendapat 403 di ruang Analyzer. Yang belum login diarahkan ke login.
- Analisis hanya menampilkan angka gabungan. Nama user dan nama item tidak tampil.
- Tautan "Analyzer" di halaman pribadi hanya muncul untuk superuser.
- Perubahan faktor berlaku juga untuk snapshot karbon di Worth to Buy. Opsi "Hitung ulang" hanya memperbarui estimasi offline, hasil Climatiq tidak diubah.

### 6. HTMX

HTMX 2.0.4 ada di `static/carbon_footprint/js/htmx.min.js`, tanpa instalasi tambahan. Prinsipnya progressive enhancement: permintaan dengan header `HX-Request: true` mendapat potongan HTML, permintaan biasa mendapat halaman penuh, jadi semua tetap jalan tanpa JavaScript.

| Halaman | Perilaku | Potongan |
|---|---|---|
| Numbers | pemilih item mengganti angka | `_numbers.html` |
| Estimates | cari (debounce 300 ms), filter, urutan, hapus + toast; URL ikut berubah | `_rows.html` |
| Form | pratinjau CO₂e, cost per wear, skor saat mengetik (selalu offline, tidak memanggil Climatiq) | `_preview.html` |
| Analisis | filter bahan, kategori, sumber data | `_analysis.html` |
| Faktor emisi | simpan, reset, dan error validasi mengganti form di tempat | `_factors_form.html` |

Toast dikirim server lewat header `HX-Trigger` (`cf:toast`) dan ditampilkan oleh `cf.js`. `cf.js` juga mengisi placeholder berat sesuai kategori, pintasan `/` untuk fokus ke kolom cari, dan penanda "diubah" pada kolom faktor. Tombol Back memakai halaman penuh (`HX-History-Restore-Request`).

### 7. Struktur

```
carbon_footprint/
  access.py        izin akses (memakai ulang peran dari worth_to_buy_analyzer.roles)
  analysis.py      agregasi untuk halaman Analyzer (anonim)
  constants.py     pilihan kategori/material, faktor bawaan, ID faktor Climatiq
  forms.py         CarbonEstimateForm, FactorsForm
  models.py        CarbonEstimate, MaterialFactor, CategoryWeight
  services.py      compute_co2e, sustainability_score, panggilan Climatiq
  views.py         semua view (versi penuh dan potongan HTMX)
  urls.py          namespace carbon_footprint
  admin.py
  management/commands/setup_analyzer.py   jalan pintas membuat grup Analyzer
  static/carbon_footprint/css/carbon_footprint.css
  static/carbon_footprint/js/{htmx.min.js,cf.js}
  templates/carbon_footprint/   index, list, form, confirm_delete, analyzer, factors, dan potongan (_*.html)
  tests.py         89 test (termasuk CarbonAdapterTests di worth_to_buy_analyzer)
```

### 8. Styling

CSS biasa, tanpa Tailwind:
- `static/css/wearwise.css` (design system bersama: token warna, sidebar, topbar), dimuat oleh `base.html` setelah `styles.css` tim.
- `carbon_footprint.css` memakai variabel dari `wearwise.css` dan menambah token `--cf-*`. Dimuat lewat `_assets.html`.
- Halaman Analyzer memakai kelas `wtb-*` dan `ref-*` milik Worth to Buy lewat `references/_layout.html`, supaya kedua modul tampil sebagai satu ruang kerja.

Catatan: `_assets.html` harus memuat CSS dan dua `<script>` (`htmx.min.js` dan `cf.js`). Tanpa dua script itu fitur HTMX tidak jalan, tapi halaman tetap berfungsi.

### 9. Konfigurasi

Tambahkan di `settings.py` (nilai rahasia jangan di-commit):
```python
import os
CLIMATIQ_API_KEY = os.environ.get("CLIMATIQ_API_KEY", "")
CLIMATIQ_DATA_VERSION = "^37"   # versi data Climatiq
```
Set variabel lingkungan sebelum menjalankan server:
```bash
# macOS/Linux
export CLIMATIQ_API_KEY="isi-api-key"
# PowerShell
$env:CLIMATIQ_API_KEY = "isi-api-key"
```
Tanpa API key, modul tetap berjalan memakai estimasi offline.

### 10. Pemasangan

1. Salin app `carbon_footprint/` ke proyek, tambahkan ke `INSTALLED_APPS`, dan sertakan URL: `path("carbon/", include("carbon_footprint.urls"))`.
2. Buat dan jalankan migrasi:
   ```bash
   python manage.py makemigrations carbon_footprint
   python manage.py migrate
   ```
3. Opsional: set `CLIMATIQ_API_KEY` di environment atau settings (lihat bagian Konfigurasi).
4. Beri peran Analyzer ke akun yang perlu lewat admin (atau `python manage.py setup_analyzer` untuk lokal).
5. Di `worth_to_buy_analyzer`, adapter karbon memakai `carbon_footprint.services.compute_co2e`.
6. Jalankan server:
   ```bash
   python manage.py runserver
   ```

### 11. Pengujian

```bash
python manage.py test carbon_footprint
python manage.py test worth_to_buy_analyzer.tests.CarbonAdapterTests
```
Test berjalan offline (API key dikosongkan dan panggilan jaringan diblokir) lewat `OfflineTestCase`, jadi tidak memanggil Climatiq sungguhan dan hasilnya sama di semua komputer. Cakupannya: konsistensi konstanta, rumus skor, parsing balasan Climatiq, fallback, CRUD termasuk pembatasan akses antar user, serta akses per peran.

Test yang memanggil `compute_co2e` harus memakai `TestCase` (bukan `SimpleTestCase`), karena faktor dibaca dari database.

### 12. Catatan dan batasan

- Faktor offline per material berasal dari data publik (CAEP 2022, basis produksi Tiongkok), jadi sifatnya perkiraan kasar, bukan angka resmi untuk Indonesia. Analyzer dapat menyesuaikannya lewat halaman faktor emisi.
- Faktor berbasis pengeluaran (CEDA) menghitung emisi dari nilai uang, sehingga barang mahal berbahan sama bisa tampak lebih berdampak daripada yang murah.
- Pratinjau di form selalu memakai estimasi offline, jadi angkanya bisa berbeda dari hasil akhir bila Climatiq dipakai saat menyimpan.
- Data bahan dari database berlisensi (misalnya ecoinvent) tidak dipakai karena memerlukan langganan Climatiq.



### Modul 4: Repair & Clothing Lifecycle (`lifecycle`)

Mencatat kondisi pakaian yang sudah dimiliki, lalu memberi rekomendasi apakah pakaian sebaiknya di-**repair**, **reuse**, atau **recycle**, lengkap dengan panduan langkahnya. Tujuannya supaya pakaian dipakai selama mungkin sebelum dibuang.

#### Fitur
- CRUD catatan kondisi: tambah, lihat riwayat, ubah, dan hapus. Setiap catatan hanya bisa diakses oleh pemiliknya.
- Dropdown pakaian hanya berisi pakaian milik user sendiri (dari modul Wardrobe).
- Rekomendasi dihitung otomatis dari kondisi setiap kali catatan dibuat atau diubah.
- AJAX: tambah catatan, filter, ubah status, dan hapus tanpa reload halaman.
- Filter riwayat berdasarkan rekomendasi dan status tindak lanjut.
- Repair guide berisi langkah praktis untuk Repair, Reuse, dan Recycle.
- Endpoint JSON untuk data riwayat milik user yang login.

#### Aturan rekomendasi
| Kondisi | Rekomendasi |
|---|---|
| Masih bagus | Reuse |
| Rusak ringan | Repair |
| Rusak berat | Repair |
| Tidak layak pakai | Recycle |

Aturan dan isi repair guide ada di `lifecycle/services.py`.

#### Model `ConditionRecord`
`user`, `item` (relasi ke `ClothingItem` milik Wardrobe), `condition`, `damage_description`, `notes`, `recommendation`, `status` (Belum ditindaklanjuti / Sedang dikerjakan / Selesai), `created_at`, `updated_at`.

#### URL
| Path | Nama | Fungsi |
|---|---|---|
| `/lifecycle/` | `lifecycle:index` | Riwayat, form tambah, filter, dan repair guide |
| `/lifecycle/create/` | `lifecycle:create` | Tambah catatan (tanpa AJAX) |
| `/lifecycle/<id>/edit/` | `lifecycle:update` | Ubah catatan |
| `/lifecycle/<id>/delete/` | `lifecycle:delete` | Konfirmasi dan hapus catatan |
| `/lifecycle/json/` | `lifecycle:json` | Data riwayat dalam JSON |
| `/lifecycle/ajax/create/` | `lifecycle:create_ajax` | Tambah catatan via AJAX (POST) |
| `/lifecycle/<id>/ajax/status/` | `lifecycle:status_ajax` | Ubah status via AJAX (POST) |
| `/lifecycle/<id>/ajax/delete/` | `lifecycle:delete_ajax` | Hapus via AJAX (POST) |

Semua halaman wajib login. Mengakses catatan milik user lain menghasilkan 404.

#### Pengujian
```bash
python manage.py test lifecycle
```
28 test mencakup aturan rekomendasi, repair guide, CRUD, filter, JSON, AJAX, dan pembatasan akses antar user.

#### Struktur
```
lifecycle/
├── services.py    # aturan rekomendasi dan isi repair guide
├── models.py  forms.py  views.py  urls.py  admin.py
├── templates/lifecycle/   # list, form, confirm_delete, field
├── static/lifecycle/css/lifecycle.css   # tampilan halaman Lifecycle
├── static/lifecycle/js/lifecycle.js     # AJAX
└── tests.py
```