# Panduan akun Analyzer

Analyzer adalah akun khusus yang mengelola referensi pakaian. User biasa memakai
referensi terbit untuk memulai analisis pribadi; admin mengelola akun dan role.
Pengelolaan referensi merupakan bagian Worth to Buy Analyzer (Modul-2).

## Menyiapkan database

Dari folder proyek dengan virtual environment aktif:

```bash
python manage.py migrate worth_to_buy_analyzer
python manage.py runserver
```

Migrasi `0004` menambahkan tabel `ClothingReference`; `0005` membuat grup
`Analyzer`. Keduanya tidak mengubah data analisis lama atau otomatis memberikan
role kepada akun yang sudah ada. Pada laptop pengembang migrasi ini sudah
dijalankan; lingkungan anggota kelompok dan PWS perlu menjalankannya juga.

## Memberikan role melalui admin

1. Siapkan akun biasa untuk pengguna yang akan menjadi Analyzer melalui halaman
   daftar, atau buat akunnya di Django admin.
2. Login sebagai superuser di `/admin/`. Jika belum memiliki superuser lokal,
   buat sendiri melalui `python manage.py createsuperuser`; isikan kredensial
   langsung di Terminal, jangan disimpan di source atau dokumentasi.
3. Buka **Users**, pilih akun Analyzer tersebut, lalu pada **Groups** pindahkan
   grup **Analyzer** ke daftar grup yang dipilih dan simpan.
4. Akun Analyzer cukup berstatus **Active**. Tidak perlu mengaktifkan **Staff
   status** atau **Superuser status**, serta tidak perlu memberi akses data user.
5. Logout dari akun admin. Login sebagai akun Analyzer melalui `/login/`.
   Sistem mengarahkannya ke `/worth-to-buy/workspace/` dengan menu Analyzer.
6. Untuk mengembalikan akun menjadi user biasa, admin menghapus keanggotaannya
   dari grup Analyzer. Referensi yang sudah dibuat tetap ada beserta penulisnya.

Role ditentukan server. Form registrasi tidak menerima pemilihan role. Login
admin diarahkan ke Django admin; login user biasa tetap ke beranda atau tujuan
`next` lokal yang valid. Untuk Analyzer, `next` hanya dipertahankan jika menuju
ruang Analyzer agar tautan lama ke halaman user tidak mengubah alur login.

## Alur kerja

- Analyzer dapat menambah, melihat, mengedit, serta menghapus referensi bersama
  lewat ruang khusus. Nama pakaian, kategori, harga positif, dan sumber data
  wajib diisi. Bahan dan berat boleh sama-sama kosong atau sama-sama diisi.
- Referensi baru menjadi **draft** jika pilihan publikasi belum dicentang.
  Draft hanya dapat dibuka di ruang Analyzer atau oleh superuser.
- Centang **Tampilkan di katalog user** lalu simpan untuk menerbitkan. Hilangkan
  centang dan simpan untuk menarik referensi dari katalog.
- User membuka **Worth to Buy → Referensi pakaian → Gunakan referensi**. Identitas,
  merek, harga, bahan/berat, dan link produk menjadi isian awal yang bisa diubah.
  Kebutuhan, budget, target biaya, serta rencana pemakaian tetap diisi user.
- Referensi hanya menyalin isian awal. Edit, penarikan, atau penghapusan referensi
  tidak mengubah hasil analisis pribadi yang sudah disimpan. Form yang sudah
  terbuka juga tetap bisa dikirim setelah referensi dihapus.
- Referensi mencatat akun pembuat, pengubah terakhir, dan waktu perubahan. Akun
  Analyzer tidak bisa membaca atau mengubah analisis pribadi user dari modul ini.
- Superuser bisa membuka ruang Analyzer serta mengelola referensi di Django
  admin. Staff biasa yang tidak memiliki role Analyzer tidak mendapat akses
  ruang Analyzer. Pemeriksaan berlaku pada server, bukan hanya menu.
- Katalog memakai data lokal yang dimasukkan Analyzer. Tidak ada katalog produk
  eksternal atau angka contoh yang otomatis ditambahkan ke database pengguna.

## URL dan akses

Semua nama URL berada di namespace `worth_to_buy_analyzer`.

| URL | Nama | Akses |
| --- | --- | --- |
| `/worth-to-buy/workspace/` | `reference_list` | Analyzer / superuser; cari, filter draft/terbit, paginasi |
| `/worth-to-buy/workspace/new/` | `reference_create` | Analyzer / superuser; GET form, POST simpan |
| `/worth-to-buy/workspace/<pk>/` | `reference_detail` | Analyzer / superuser; GET detail |
| `/worth-to-buy/workspace/<pk>/edit/` | `reference_update` | Analyzer / superuser; GET form, POST edit/publikasi |
| `/worth-to-buy/workspace/<pk>/delete/` | `reference_delete` | Analyzer / superuser; GET konfirmasi, POST hapus |
| `/worth-to-buy/catalogue/` | `catalogue` | User biasa / superuser; hanya referensi terbit |
| `/worth-to-buy/new/?reference=<pk>` | `create` | User biasa / superuser; isi awal dari referensi terbit |

Semua penulisan memerlukan POST dan CSRF. Permintaan user biasa ke ruang Analyzer
menghasilkan 403, sedangkan akses anonim diarahkan ke login. Draft atau ID
referensi tidak valid tidak bisa dipakai untuk mengisi awal form user.

## Verifikasi 27 Oktober 2026

- 70 tes analyzer dan karbon lulus, termasuk 17 tes baru untuk pemisahan role,
  tujuan login, penolakan pemalsuan role saat registrasi, CRUD referensi,
  pencatatan penulis, draft/publikasi, CSRF, privasi, serta penggunaan katalog.
- `makemigrations worth_to_buy_analyzer --check --dry-run` bersih.
- Browser diuji dengan akun dan database sementara: login Analyzer, menerbitkan
  referensi, login user, memakai referensi, dan menyimpan hasil analisis.
- Perubahan tetap di branch `Modul-2`; commit, push, dan review PR ditangani
  pengembang sesuai alur kelompok. Migrasi dan pengujian PWS belum dilakukan.

## Commit perubahan Modul-2

Periksa `git status` dan pastikan branch saat ini `Modul-2`. Masukkan hanya file
perubahan fitur ini, termasuk sambungan login bersama:

```bash
git add README.md main/views.py static/css/worth_to_buy.css static/css/analyzer_workspace.css worth_to_buy_analyzer/
git diff --cached --stat
git commit -m "feat: add analyzer role and clothing reference catalogue"
```

Jika sudah siap untuk direview kelompok, jalankan `git push origin Modul-2`.
Jangan masukkan file environment, database lokal, atau kredensial akun ke commit.
