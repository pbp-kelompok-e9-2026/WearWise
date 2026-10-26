# Styling WearWise (dari desain Figma)

## Isi paket
- `static/css/wearwise.css` : seluruh design system (token warna, sidebar, topbar, semua halaman).
- `templates/base.html` : shell baru (sidebar + topbar + pesan flash). Ganti base.html lama.
- `templates/partials/footer.html` : footer halaman About.
- `main/templates/main/` : home.html, about.html, login.html, register.html.
- `templates/design_reference/` : contoh markup Discover, Worth to Buy, Wardrobe, Lifecycle, Profile (data masih contoh). Salin ke template modul masing-masing.
- `carbon_footprint/` : template dan CSS modulmu yang sudah diselaraskan dengan shell baru (timpa file lama).

## Langkah
1. Salin `static/css/wearwise.css` ke `static/css/`. Salin `templates/` ke folder templates proyek.
2. Salin `main/templates/main/*` ke `main/templates/main/`.
3. Timpa file di `carbon_footprint/templates/carbon_footprint/` dan `carbon_footprint/static/carbon_footprint/css/`.
4. Tambah view dan URL di app `main` (nama dipakai oleh sidebar):
   ```python
   # main/views.py
   def show_main(request):  return render(request, "main/home.html")
   def about(request):      return render(request, "main/about.html")
   # main/urls.py  (app_name = "main")
   path("", show_main, name="show_main"),
   path("about/", about, name="about"),
   ```
5. Sidebar mencari nama URL berikut. Kalau namanya beda di proyekmu, ubah di bagian atas `base.html`
   (link yang tidak ketemu otomatis menjadi `#`, tidak error):
   `main:show_main, main:about, main:profile, main:login, main:register, main:logout,
   carbon_footprint:index, wardrobe:index, dashboard:discover, dashboard:worth_to_buy, dashboard:lifecycle`
6. `base.html` memuat `css/styles.css` (CSS tim) lalu `css/wearwise.css`. Urutan ini penting. wearwise.css memetakan ulang token `--color-*` tim ke palet Figma, jadi halaman lama ikut berubah warna.
7. Halaman tim yang masih memakai kelas Tailwind perlu diganti ke kelas `ww-` (lihat `design_reference/`).
8. Jalankan `python manage.py makemigrations carbon_footprint`, `migrate`, lalu set `CLIMATIQ_API_KEY` bila ingin data Climatiq.

## Yang perlu kamu cek
- Font: Instrument Serif (judul) dan Hanken Grotesk (teks) dipilih dengan mencocokkan tampilan PDF. Kalau di Figma fontnya lain, ganti dua variabel `--ww-font-display` dan `--ww-font-body`, serta link Google Fonts di base.html.
- Gambar produk masih berupa blok gradien (`.ww-img`). Ganti dengan `<img class="ww-img" src="...">`.
- Judul Home memakai bold sintetis supaya mirip Figma (`.ww-display`).
- Sudah diuji di 1920, 1280 dan 390 px. Perbedaan dengan desain pada 1920x1080 sekitar beberapa piksel.
- Saran: ubah `FALLBACK_DEFAULT_KG_CO2E_PER_KG` di constants.py menjadi sekitar 20.7 agar sesuai nilai bahan terbaru.

## Sidebar buka/tutup
Tombol hamburger ada di kiri topbar. Statusnya disimpan di localStorage (`ww-sidebar`), jadi tetap sama setelah pindah halaman. Di layar kecil (<= 900px) sidebar tertutup secara default. Halaman login dan register tidak memakai tombol ini.

## Konten polos
Halaman yang hanya berisi h1, p, h2, dst. tanpa kelas `ww-` otomatis mendapat gutter 80px, jadi tidak menempel ke sidebar. Untuk tata letak khusus, pakai kelas `ww-page`.

## Profile (dashboard)
`dashboard/templates/dashboard/profile.html` menggantikan profile.html lama. Variabel konteks `phone`, `address`, `wears_logged`, `avg_cost_per_wear`, `sustainability_score` tetap dipakai (ada nilai default bila tidak dikirim). View dan URL: lihat balasan di chat.
