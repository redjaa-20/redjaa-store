# 🖥️ Panduan Full CMD — GitHub & VPS (Tanpa Aplikasi GUI)

Semua langkah pakai Command Prompt (CMD) Windows. Tidak perlu GitHub Desktop, FileZilla, dll.
`ssh`, `scp`, dan `winget` sudah bawaan Windows 10/11.

---

## 0️⃣ Install Git via CMD (sekali saja)

Cek apakah Git sudah ada:

```cmd
git --version
```

Kalau muncul "not recognized", install pakai winget:

```cmd
winget install --id Git.Git -e --source winget
```

Setelah selesai, **tutup CMD dan buka lagi** agar `git` dikenali. Cek ulang:

```cmd
git --version
```

Set identitas Git (sekali saja):

```cmd
git config --global user.name "Nama Anda"
git config --global user.email "email@anda.com"
```

---

## BAGIAN 1 — Upload ke GitHub (dari CMD)

### 1️⃣ Buat Repo di GitHub

Langkah ini tetap lewat browser (buat repo):

1. https://github.com → tombol **+** → **New repository**
2. Nama: `redjaa-digital-bot`
3. Pilih **Private**
4. Jangan centang apa pun, klik **Create repository**

### 2️⃣ Buat Personal Access Token (untuk login dari CMD)

GitHub tidak menerima password biasa dari CMD. Buat token:

1. https://github.com/settings/tokens → **Tokens (classic)**
2. **Generate new token (classic)**
3. Centang scope **repo**
4. **Generate** → salin token (simpan, hanya muncul sekali)

Token ini dipakai sebagai "password" saat `git push`.

### 3️⃣ Init & Push (di CMD)

```cmd
cd /d "d:\Develop\Telegram\Bot\redjaa-digital"

git init
git add .
git commit -m "Initial commit - QuantumVault bot"
git branch -M main
git remote add origin https://github.com/USERNAME/redjaa-digital-bot.git
git push -u origin main
```

Saat diminta:

- **Username**: username GitHub Anda
- **Password**: tempel **token** tadi (bukan password akun)

> ✅ File `.env`, `data.json`, `qris.jpg` otomatis dilewati berkat `.gitignore`.

---

## BAGIAN 2 — Setup di VPS (via SSH dari CMD)

### 1️⃣ Login SSH (dari CMD Windows)

```cmd
ssh ubuntu@43.156.134.165
```

Ketik `yes` jika ditanya fingerprint pertama kali, lalu masukkan password VPS.

### 2️⃣ Install Git & Python di VPS

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-pip python3-venv
```

### 3️⃣ Clone Repo (repo private → pakai token)

```bash
cd ~
git clone https://github.com/USERNAME/redjaa-digital-bot.git redjaa-digital
```

Masukkan username GitHub & token saat diminta.

Simpan kredensial agar tidak diminta terus:

```bash
git config --global credential.helper store
```

(setelah `git pull` berikutnya, token tersimpan)

### 4️⃣ Setup venv & Dependencies

```bash
cd ~/redjaa-digital
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## BAGIAN 3 — Kirim File Rahasia ke VPS (dari CMD Windows)

`.env` dan `qris.jpg` tidak ada di GitHub, jadi kirim manual pakai `scp`.

**Buka CMD BARU di Windows** (jangan yang sedang SSH), lalu:

```cmd
scp "d:\Develop\Telegram\Bot\redjaa-digital\.env" ubuntu@43.156.134.165:/home/ubuntu/redjaa-digital/

scp "d:\Develop\Telegram\Bot\redjaa-digital\qris.jpg" ubuntu@43.156.134.165:/home/ubuntu/redjaa-digital/
```

> Alternatif: buat `.env` langsung di VPS pakai `nano .env` lalu isi manual.

---

## BAGIAN 4 — Jalankan Bot 24/7 (systemd)

Kembali ke sesi SSH di VPS:

```bash
sudo cp ~/redjaa-digital/redjaa-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable redjaa-bot
sudo systemctl start redjaa-bot
sudo systemctl status redjaa-bot
```

Kalau `active (running)` hijau → bot sudah jalan. Keluar SSH dengan `exit`.

---

## BAGIAN 5 — Workflow Update Sehari-hari

### Di Windows (CMD), setelah edit kode:

```cmd
cd /d "d:\Develop\Telegram\Bot\redjaa-digital"
git add .
git commit -m "Deskripsi perubahan"
git push
```

### Di VPS (SSH dari CMD), tarik update:

```cmd
ssh ubuntu@43.156.134.165
```

Lalu di VPS:

```bash
cd ~/redjaa-digital
git pull
sudo systemctl restart redjaa-bot
exit
```

---

## BAGIAN 6 (OPSIONAL) — Update VPS dengan 1 Perintah

Buat script di VPS (via SSH):

```bash
nano ~/redjaa-digital/update.sh
```

Isi:

```bash
#!/bin/bash
cd ~/redjaa-digital
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart redjaa-bot
echo "✅ Update selesai!"
sudo systemctl status redjaa-bot --no-pager -l | head -n 5
```

Beri izin:

```bash
chmod +x ~/redjaa-digital/update.sh
```

Ke depannya, update cukup:

```bash
~/redjaa-digital/update.sh
```

---

## 📋 Ringkasan Perintah Penting

### CMD Windows

| Perintah                                         | Fungsi            |
| ------------------------------------------------ | ----------------- |
| `git add . && git commit -m "pesan" && git push` | Upload perubahan  |
| `ssh ubuntu@43.156.134.165`                      | Masuk ke VPS      |
| `scp "file" ubuntu@IP:/path/`                    | Kirim file ke VPS |

### Di VPS (Ubuntu)

| Perintah                            | Fungsi             |
| ----------------------------------- | ------------------ |
| `git pull`                          | Tarik kode terbaru |
| `sudo systemctl restart redjaa-bot` | Restart bot        |
| `sudo systemctl status redjaa-bot`  | Cek status         |
| `sudo journalctl -u redjaa-bot -f`  | Lihat log realtime |
| `exit`                              | Keluar dari SSH    |

---

## ❓ Troubleshooting

**`git` not recognized setelah install:**
Tutup semua CMD, buka baru. Kalau masih, restart komputer.

**`ssh`/`scp` not recognized:**
Aktifkan OpenSSH Client:

```cmd
dism /online /Add-Capability /Capability:OpenSSH.Client~~~~0.0.1.0
```

**`git push` ditolak / auth failed:**
Pastikan pakai **token** sebagai password, bukan password akun GitHub.

**`git pull` error "local changes":**

```bash
git reset --hard origin/main
git pull
```

⚠️ Menghapus perubahan lokal di VPS yang belum di-commit.
