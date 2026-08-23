# 🤖 QuantumVault Telegram Bot

Bot Telegram untuk panel distributor QuantumVault dengan 3 menu utama:

- 🛒 **Beli** — Beli produk/layanan dari daftar yang tersedia
- 💰 **Cek Saldo** — Cek saldo akun dari API QuantumVault
- 👤 **Info Akun** — Lihat info user (ID, tanggal bergabung, dll)

---

## 📁 Struktur File

```
├── bot.py            # File utama bot Telegram
├── api_client.py     # Client untuk komunikasi dengan API QuantumVault
├── config.py         # Konfigurasi (token, API key)
├── requirements.txt  # Dependency Python
└── README.md         # Dokumentasi
```

---

## ⚙️ Instalasi & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Buat Bot Telegram

1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot` dan ikuti instruksi
3. Salin **token** yang diberikan

### 3. Konfigurasi

Edit file `config.py`:

```python
# Token dari BotFather
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# API Key dari QuantumVault (lihat di quantumvault.me/?tab=api)
QUANTUMVAULT_API_KEY = "api_key_anda_disini"

# Base URL API (sesuaikan jika berbeda)
QUANTUMVAULT_API_URL = "https://quantumvault.me/api"
```

### 4. Jalankan Bot

```bash
python bot.py
```

---

## 🎮 Cara Menggunakan

| Command  | Fungsi                     |
| -------- | -------------------------- |
| `/start` | Mulai bot & tampilkan menu |
| `/menu`  | Tampilkan menu utama       |
| `/batal` | Batalkan proses pembelian  |

---

## 🔧 Penyesuaian API

Jika response API dari QuantumVault berbeda, sesuaikan parsing di `api_client.py`:

- **Cek Saldo**: Sesuaikan key `balance` di method `get_balance()`
- **Info Akun**: Sesuaikan key `id`, `created_at`, `email` di method `get_profile()`
- **Daftar Layanan**: Sesuaikan key `service`, `name`, `rate` di method `get_services()`
- **Buat Pesanan**: Sesuaikan parameter `service`, `quantity`, `link` di method `create_order()`

---

## 📝 Catatan

- Pastikan API Key QuantumVault sudah benar dan memiliki akses yang cukup
- Bot menggunakan **Inline Keyboard** untuk navigasi yang lebih nyaman
- Data pesanan sementara disimpan di memori (akan hilang saat bot restart)
