# Catatan integrasi Worth to Buy Analyzer

## Arahan kelompok (21–26 Oktober 2026)

- Simpan pekerjaan lokal sebelum mengambil perubahan kelompok. Jangan menimpa
  CSS lama dengan hasil pull tanpa membandingkan keduanya.
- Arahan awal 21 Oktober: salin styling analyzer dahulu, pisahkan styling dashboard
  ke `static/css/dashboard.css`, lalu integrasikan. Ini konteks historis; jangan
  menempelkan CSS lama kembali ke hasil frontend terbaru secara otomatis.
- Pisahkan CSS per halaman/modul untuk mengurangi konflik, gunakan selector yang
  dibatasi pada modul, dan sepakati nama serta nilai variabel warna bersama.
- Ikuti template/Figma kelompok. Gunakan CSS biasa dan JS/HTMX; jangan menambahkan
  Tailwind. Styling awal analyzer sebelumnya belum merupakan hasil final Figma.
- Zidan sedang menangani perapihan frontend, termasuk Worth to Buy Analyzer.
  Khalishah menangani alur backend input calon pakaian sampai hasil worth-to-buy;
  Zidan menangani perhitungan karbon/sustainability.
- Diskusi nama mengarah ke WiseFit. Perubahan nama global mengikuti keputusan
  kelompok dan tidak dilakukan oleh patch backend ini.
- API key hanya lewat environment/`.env` yang diabaikan Git. Nilai key dari chat
  sengaja tidak disimpan dalam catatan, source, fixture, maupun commit.
- Integrasi kelompok menggunakan commit, push, dan pull request yang ditinjau.
  Patch backend diajukan melalui branch terpisah; merge menunggu review kelompok.

## Dasar pekerjaan

Branch `codex/analyzer-backend` dibuat dalam worktree terpisah dari
`origin/main` pada commit `e85f62d`. Commit `origin/Modul-2` (`2bf7e26`) sudah
menjadi ancestor `main`, sehingga pekerjaan modul sebelumnya tetap tercakup.
Checkout asli `Modul-2` tidak di-pull atau diubah. CSS dan template dasar kelompok
tidak diubah oleh patch backend ini.

## Menjalankan setelah integrasi

1. Aktifkan virtual environment kelompok dan pasang dependensi `requirements.txt`.
2. Jalankan `python manage.py migrate`. Migrasi analyzer `0002` hanya menambah
   `material` (boleh kosong) dan `weight_kg` (boleh NULL); data lama tetap tersimpan.
3. Jalankan `python manage.py check` dan
   `python manage.py test worth_to_buy_analyzer --noinput`.
4. Jalankan server lokal dan buka `/worth-to-buy/`. Pengguna diarahkan ke login
   kelompok di `/accounts/login/?next=/worth-to-buy/` jika belum masuk.
5. Buat analisis, buka detail, edit pemakaian, simpan keputusan, lalu coba hapus
   lewat halaman konfirmasi. Akun lain tidak boleh mengakses objek tersebut.

## Kontrak untuk frontend Zidan

Template khusus modul berada di `worth_to_buy_analyzer/templates/worth_to_buy_analyzer/`.
Semua mewarisi `_layout.html`, yang mewarisi `base.html` kelompok. Selector baru
memakai awalan `wtb-`; belum ada CSS baru atau Tailwind. Silakan terapkan desain
Figma pada template ini, pertahankan nama field, named URL, error form, dan CSRF.

Namespace semua URL: `worth_to_buy_analyzer`.

| Nama URL | Path relatif terhadap `/worth-to-buy/` | Metode / fungsi |
| --- | --- | --- |
| `analyzer` | kosong | GET: riwayat milik pengguna, 10 item/halaman (`?page=2`) |
| `create` | `new/` | GET form; POST validasi, hitung snapshot karbon bila lengkap, simpan, redirect ke detail |
| `detail` | `<pk>/` | GET hasil analisis |
| `update` | `<pk>/edit/` | GET form; POST validasi dan simpan perubahan |
| `delete` | `<pk>/delete/` | GET konfirmasi; POST hapus |
| `decide` | `<pk>/decision/` | POST keputusan dan catatan |
| `refresh_carbon` | `<pk>/refresh-carbon/` | POST hitung ulang snapshot karbon |

- Ini form HTML Django biasa, bukan JSON API. Submit berhasil memakai pola
  POST → redirect → GET; input salah menampilkan halaman yang sama beserta error.
- Context form: `form`, `item`, `mode` (`create`/`update`). Render `form` atau
  masing-masing bound field agar label, nilai, pilihan, help text, dan error tetap tampil.
- Input: `clothing_name`, `category`, `brand`, `product_url`, `existing_clothing`,
  `purpose`, `price`, `budget`, `expected_wears`, `target_cpw`, `wears_per_month`,
  `material`, `weight_kg`. Daftar pilihan berasal dari field form/model.
- Harga/budget/target memakai rupiah, berat memakai kg, jumlah pemakaian adalah
  total selama kepemilikan. Jangan kirim `Rp`, pemisah ribuan, atau satuan dalam
  nilai angka. Material dan berat harus sama-sama kosong atau sama-sama diisi.
- Context detail: `item`, `result`, `decision_form`. `result` memuat
  `cost_per_wear`, `purchase_score`, `score_breakdown`, `within_budget`,
  `meets_cpw_target`, `wears_to_target`, `months_to_target`, `recommendation`,
  `recommendation_label`, `reason`, `rule_version`, dan `carbon_per_wear`.
- `owner`, versi aturan, timestamp, dan snapshot karbon ditentukan server.
  Kiriman field tambahan tidak bisa mengubah kepemilikan atau memalsukan hasil.
- Keputusan pengguna terpisah dari rekomendasi otomatis. Form keputusan hanya
  menerima `decision` dan `decision_note`. Perubahan isian analisis mereset
  status keputusan/timestamp agar ditinjau ulang, tetapi mempertahankan catatan.
- Semua endpoint perlu login. ID milik pengguna lain menghasilkan 404; semua
  mutasi perlu POST dengan `{% csrf_token %}`. Refresh karbon tidak dilakukan
  saat GET detail atau riwayat.

## Aturan analisis versi 1

Belum ada rumus purchase score dalam kode awal. Versi ini adalah usulan aturan
aplikasi yang transparan dan perlu disepakati kelompok, bukan standar ilmiah,
bukan sustainability score Zidan, dan bukan skor yang diberikan Climatiq.

- CPW = harga / total perkiraan pemakaian, dihitung dengan Decimal.
- Poin CPW = 40 × min(1, target CPW / CPW).
- Poin budget = 30 × min(1, budget / harga).
- Poin pakaian serupa = 20 jika belum punya, 10 jika perlu diperbaiki, 0 jika masih layak.
- Poin tujuan = 10 untuk rutin/penggantian, 5 untuk acara tertentu, 0 untuk variasi.
- Jumlah dibulatkan half-up ke bilangan bulat 0–100; rincian ditampilkan pada hasil.
- Perbandingan budget dan target memakai nilai belum dibulatkan. Tampilan CPW
  dibulatkan half-up ke dua desimal.
- Minimal pemakaian untuk target = ceil(harga / target CPW). Jika frekuensi bulanan
  diisi, perkiraan bulan = ceil(minimal pemakaian / frekuensi bulanan).
- Rekomendasi berdasarkan prioritas: pakai yang masih layak → perbaiki yang
  repairable → tunda bila melebihi budget → pinjam/sewa untuk acara tertentu →
  cari alternatif jika CPW di atas target → tunda untuk variasi → beli dengan
  rencana pemakaian. Skor tinggi tidak mengesampingkan prioritas tersebut.
- Hasil purchase score dihitung dari input tersimpan saat dibuka. Jika aturan
  berubah di masa depan, tambah versi aturan dan strategi kompatibilitas hasil lama.

## Hubungan dengan modul karbon

- Adapter hanya memanggil `carbon_footprint.services.compute_co2e(material,
  weight_kg, price)` dan memakai pilihan material dari modul itu.
- Material dan berat disimpan di analyzer; patch ini tidak mengubah model,
  faktor emisi, API key, atau file modul karbon, dan tidak membuat baris
  `CarbonEstimate` otomatis. Kedua modul menyimpan riwayatnya masing-masing.
- Snapshot dihitung ketika membuat analisis atau mengubah harga/material/berat;
  mengubah nama/jumlah pemakaian tidak memanggil API lagi. Tombol refresh
  memungkinkan percobaan ulang saat layanan sebelumnya gagal.
- `carbon_kg_co2e=None` berarti belum tersedia, bukan emisi nol. Snapshot lama
  dikosongkan jika input berubah dan estimasi baru gagal.
- Sumber `climatiq` ditandai berbasis harga IDR (CEDA 2025/Indonesia), sedangkan
  `fallback` ditandai tabel cadangan berbasis berat/material. Referensi, batas
  cakupan, dan timestamp disimpan agar hasil tidak mengklaim sumber yang keliru.
- Tes tidak menggunakan API key asli atau memanggil API eksternal; jalur API
  diuji dengan mock, dan jalur offline diuji dengan fungsi karbon yang sebenarnya.

## Sambungan login dan perhatian integrasi

`base.html` kelompok memanggil named URL `login`/`logout`, tetapi `main` pada
`e85f62d` belum mendaftarkannya. Patch ini menambahkan dua route di `WearWise/urls.py`
memakai LoginView/LogoutView bawaan Django dan template `login.html` yang sudah ada.
Login mengikuti `next` lokal; tanpa `next` kembali ke analyzer.

Logout Django memakai POST + CSRF. Link GET logout lama dalam `base.html` perlu
Zidan ubah menjadi form POST saat merapikan frontend. Template bersama sengaja
tidak diedit bersamaan dengan pekerjaannya. Jika hasil frontend terbaru sudah
menambahkan route login/logout, gabungkan tanpa membuat route duplikat dan
pertahankan nama yang disepakati.

## Temuan di luar modul analyzer

- Tes wardrobe `test_wardrobe_url_protected` mengharapkan redirect login, tetapi
  view sekarang menghasilkan 200. Ini juga gagal pada salinan `main` sebelum patch.
- Dua ekspektasi tes karbon masih memakai faktor lama (cotton 4.00 dan linen
  1.25), sedangkan service dengan konstanta saat ini menghasilkan 9.06 dan 4.05
  pada input tes tersebut. Penyelarasan faktor/tes perlu ditangani pemilik modul.
- `makemigrations --check --dry-run` seluruh proyek melaporkan perubahan
  `dashboard.Profile.user` yang belum dimigrasikan. Ini juga terjadi pada salinan
  `main` sebelum patch. Patch ini tidak membuat migrasi modul dashboard.
- Discovery `manage.py test` tanpa label melewatkan tes karbon pada struktur
  saat ini (package karbon tidak memiliki `__init__.py`). Untuk pemeriksaan
  lintas modul, sebutkan `carbon_footprint.tests` secara eksplisit.

## Hasil verifikasi 26 Oktober 2026

- 30 tes analyzer lulus: aturan perhitungan, batas angka termasuk PostgreSQL,
  CRUD, redirect login, CSRF, pemisahan data pengguna, escaping HTML, keputusan,
  sumber karbon, pemulihan kegagalan, dan invalidasi snapshot lama.
- Migrasi analyzer `0001` → `0002` diuji pada database sementara berisi data lama;
  harga, keputusan, catatan, dan snapshot karbon tetap utuh. Checkout/database
  asli pengguna tidak digunakan untuk pengujian.
- `manage.py check` dan pemeriksaan migrasi khusus analyzer lulus; tidak ada
  perubahan model analyzer yang belum dimigrasikan.
- Tes lintas modul eksplisit: 20 tes, 17 lulus dan 3 gagal pada kasus yang
  dijelaskan di atas. Salinan `main` sebelum patch memiliki 2 kegagalan dan
  5 error karena named URL logout hilang; sambungan auth menghilangkan error
  tersebut dan membuka satu assertion faktor karbon lama yang sebelumnya tertutup.
- Pemeriksaan migrasi seluruh proyek pada salinan `main` dan branch ini sama-sama
  melaporkan perubahan `dashboard.Profile.user` yang belum dimigrasikan.
- Tidak ada pengujian live terhadap PWS/API Climatiq atau perubahan styling.
  Tampilan final tetap perlu ditinjau bersama hasil frontend Zidan.
