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

### Modul 3: Carbon Footprint & Sustainability (`carbon_footprint`)

Menghitung estimasi jejak karbon (kg CO₂e) tiap pakaian, lalu menampilkan biaya per pemakaian dan skor keberlanjutan. Halaman utamanya bernama **Numbers**.

#### Fitur
- CRUD estimasi: tambah, lihat daftar, ubah, dan hapus. Setiap estimasi hanya bisa diakses oleh pemiliknya.
- Halaman **Numbers** menampilkan estimasi terbaru: jumlah pemakaian, biaya per pemakaian, emisi CO₂e, dan skor keberlanjutan (0 sampai 100).
- Perhitungan hybrid:
  - Jika harga diisi dan `CLIMATIQ_API_KEY` tersedia, emisi dihitung lewat [Climatiq](https://www.climatiq.io/) memakai faktor berbasis pengeluaran untuk Indonesia (CEDA 2025). Harga dalam rupiah dikonversi otomatis ke USD oleh Climatiq.
  - Jika tidak, emisi dihitung dari **berat × faktor per material** (tabel cadangan di `constants.py`).
  - Jika panggilan Climatiq gagal, aplikasi otomatis memakai cara kedua, jadi halaman tidak error.
  - Kolom `source` pada setiap estimasi menyimpan asal angkanya (`climatiq` atau `fallback`).

#### Rumus
| Besaran | Rumus |
|---|---|
| Emisi (cadangan) | `berat_kg × faktor_material` (kg CO₂e per kg) |
| Biaya per pemakaian | `harga / estimasi_pemakaian` |
| Skor | `100 × (1 − (CO₂e / pemakaian) / 0,75)`, dibatasi 0 sampai 100 |

Angka 0,75 kg CO₂e per pemakaian adalah batas skor 0. Nilai ini dan semua faktor ada di `carbon_footprint/constants.py`.

#### Model `CarbonEstimate`
`user`, `name`, `category`, `material`, `weight_kg`, `price` (opsional), `estimated_wears` (default 30), `co2e_kg`, `source`, `created_at`, `updated_at`.
Jika berat dikosongkan, dipakai berat rata-rata per kategori.

#### URL
| Path | Nama | Fungsi |
|---|---|---|
| `/carbon/` | `carbon_footprint:index` | Halaman Numbers |
| `/carbon/estimates/` | `carbon_footprint:list` | Daftar estimasi |
| `/carbon/estimates/new/` | `carbon_footprint:create` | Tambah estimasi |
| `/carbon/estimates/<id>/edit/` | `carbon_footprint:update` | Ubah estimasi |
| `/carbon/estimates/<id>/delete/` | `carbon_footprint:delete` | Hapus (hanya POST) |

Semua halaman wajib login.

#### Konfigurasi
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
Tanpa API key, modul tetap berjalan memakai tabel cadangan.

#### Menjalankan
```bash
python manage.py makemigrations carbon_footprint
python manage.py migrate
python manage.py runserver
```

#### Pengujian
```bash
python manage.py test carbon_footprint
```
Test berjalan offline (API key dikosongkan dan panggilan jaringan diblokir), jadi hasilnya sama di semua komputer. Cakupannya: konsistensi konstanta, rumus skor, parsing balasan Climatiq, fallback, dan CRUD termasuk pembatasan akses antar user.

#### Struktur
```
carbon_footprint/
├── constants.py   # material, kategori, faktor, ID faktor Climatiq
├── services.py    # panggilan Climatiq, hitung CO₂e, skor
├── models.py  forms.py  views.py  urls.py  admin.py
├── templates/carbon_footprint/   # index, list, form, confirm_delete
├── static/carbon_footprint/css/carbon_footprint.css
└── tests.py
```

#### Catatan dan batasan
- Faktor cadangan per material berasal dari data publik (CAEP 2022, basis produksi Tiongkok), jadi sifatnya perkiraan kasar, bukan angka resmi untuk Indonesia.
- Faktor berbasis pengeluaran (CEDA) menghitung emisi dari nilai uang, sehingga barang mahal berbahan sama bisa tampak lebih berdampak daripada yang murah.
- Data bahan dari database berlisensi (misalnya ecoinvent) tidak dipakai karena memerlukan langganan Climatiq.
