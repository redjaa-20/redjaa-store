# 🚀 Panduan Deploy Bot ke VPS Ubuntu 22.04 LTS

Panduan lengkap menjalankan bot QuantumVault di VPS agar aktif 24/7.

---

## 📋 Prasyarat

- VPS Ubuntu 22.04 LTS 64-bit
- Akses SSH ke VPS (biasanya `ssh username@ip_vps`)

Di panduan ini diasumsikan username VPS Anda adalah `redjaa`. Ganti sesuai username Anda.

---

## 1️⃣ Login ke VPS & Update Sistem

```bash
ssh redjaa@IP_VPS_ANDA

sudo apt update && sudo apt upgrade -y
```

---

## 2️⃣ Install Python & Tools

Ubuntu 22.04 sudah punya Python 3.10. Install pip dan venv:

```bash
sudo apt install -y python3-pip python3-venv git
```

Cek versi:

```bash
python3 --version   # harus 3.10.x atau lebih
```

---

## 3️⃣ Upload File Bot ke VPS

Pilih salah satu cara:

### Opsi A — Pakai SCP (dari komputer Windows Anda)

Buka PowerShell/CMD di folder project lokal, lalu:

```bash
scp -r "d:\Develop\Telegram\Bot\redjaa-digital" redjaa@IP_VPS_ANDA:/home/redjaa/
```

### Opsi B — Pakai Git (jika project di GitHub)

```bash
cd ~
git clone https://github.com/USERNAME/REPO.git redjaa-digital
```

Pastikan file berikut ada di dalam folder `/home/redjaa/redjaa-digital`:

- `bot.py`, `api_client.py`, `database.py`, `config.py`
- `requirements.txt`
- `qris.jpg` (gambar QRIS Anda)
- `.env`

---

## 4️⃣ Buat Virtual Environment & Install Dependencies

```bash
cd ~/redjaa-digital

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5️⃣ Konfigurasi File `.env`

Kalau belum upload `.env`, buat baru:

```bash
nano .env
```

Isi dengan konfigurasi Anda:

```
TELEGRAM_BOT_TOKEN=token_dari_botfather
QUANTUMVAULT_API_KEY=api_key_quantumvault
QUANTUMVAULT_BASE_URL=https://www.quantumvault.me/api/v1
PROXY_URL=
ADMIN_ID=id_telegram_anda
PRICE_PER_UNIT=50000
QRIS_IMAGE_PATH=qris.jpg
PRODUCT_KEY=gemini_18_month_link
PRODUCT_NAME=Gemini 18 Month Link
SUPPORT_USERNAME=username_telegram_anda
```

Simpan: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## 6️⃣ Tes Jalankan Manual (opsional tapi disarankan)

```bash
source venv/bin/activate
python bot.py
```

Kalau muncul `✅ Bot berjalan!` dan bot merespons di Telegram, berarti sukses.
Tekan `Ctrl+C` untuk berhenti, lalu lanjut ke langkah systemd.

---

## 7️⃣ Setup systemd (agar jalan 24/7 & auto-restart)

### a. Salin file service

```bash
sudo cp ~/redjaa-digital/redjaa-bot.service /etc/systemd/system/
```

### b. Cek isi file, sesuaikan username jika perlu

```bash
sudo nano /etc/systemd/system/redjaa-bot.service
```

Pastikan `User`, `WorkingDirectory`, dan `ExecStart` sesuai path Anda.
Kalau username Anda `redjaa`, defaultnya sudah benar.

### c. Aktifkan service

```bash
sudo systemctl daemon-reload
sudo systemctl enable redjaa-bot
sudo systemctl start redjaa-bot
```

### d. Cek status

```bash
sudo systemctl status redjaa-bot
```

Kalau muncul `active (running)` warna hijau, bot sudah jalan 24/7. 🎉

---

## 📊 Perintah Berguna

| Perintah                               | Fungsi                            |
| -------------------------------------- | --------------------------------- |
| `sudo systemctl status redjaa-bot`     | Cek status bot                    |
| `sudo systemctl restart redjaa-bot`    | Restart bot (setelah update kode) |
| `sudo systemctl stop redjaa-bot`       | Hentikan bot                      |
| `sudo systemctl start redjaa-bot`      | Jalankan bot                      |
| `sudo journalctl -u redjaa-bot -f`     | Lihat log realtime                |
| `sudo journalctl -u redjaa-bot -n 100` | Lihat 100 baris log terakhir      |

---

## 🔄 Update Kode Bot

Setelah mengubah kode (upload ulang atau `git pull`):

```bash
cd ~/redjaa-digital
# (jika pakai git) git pull

sudo systemctl restart redjaa-bot
```

---

## 🔒 Catatan Keamanan

1. **Regenerate token** — jika token bot / API key pernah terekspos, buat baru:
   - Token bot: kirim `/revoke` ke @BotFather
   - API key: buat baru di quantumvault.me

2. **Lindungi `.env`** — set permission agar hanya Anda yang bisa baca:

   ```bash
   chmod 600 ~/redjaa-digital/.env
   ```

3. **Backup `data.json`** — file ini berisi data reseller & order. Backup berkala:

   ```bash
   cp ~/redjaa-digital/data.json ~/data-backup-$(date +%F).json
   ```

4. **Firewall** — bot ini pakai polling (outbound), tidak perlu buka port khusus.
   Cukup pastikan SSH aman:
   ```bash
   sudo ufw allow OpenSSH
   sudo ufw enable
   ```

---

## ❓ Troubleshooting

**Bot tidak jalan / `failed`:**

```bash
sudo journalctl -u redjaa-bot -n 50
```

Baca pesan error di log.

**Error `ModuleNotFoundError`:**
Dependencies belum terinstall di venv. Ulangi langkah 4.

**Error koneksi timeout:**
Bot sudah pakai timeout 60 detik. Kalau VPS memblokir Telegram, isi `PROXY_URL` di `.env`.

**Bot double / balas 2x:**
Pastikan hanya 1 instance jalan. Cek: `ps aux | grep bot.py`
Matikan proses manual jika ada, lalu andalkan systemd saja.
