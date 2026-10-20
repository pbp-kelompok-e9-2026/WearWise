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

### 5. Dashboard, Profile, & Modul Analyzer

**Penanggung jawab:** Brigitta Elissa Rebecca Simanjuntak (2506601855)

- **Create:** Menginput data ke database untuk dianalisis dan mengikuti eco challenge baru
- **Read:** Melihat statistik wardrobe, money saved, carbon saved, progres eco challenge, dan profile
- **Update:** Mengubah data profile, progres eco challenge, dan data database yang sudah diinput
- **Delete:** Menghapus data database yang tidak diperlukan dan keluar dari eco challenge

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
- Input database untuk dianalisis

### 3. Admin
- Mengelola data user
- Monitor perilaku user atau problem