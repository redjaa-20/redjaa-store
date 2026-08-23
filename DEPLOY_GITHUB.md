# 🔄 Panduan Upload ke GitHub & Auto-Update di VPS

Panduan agar setiap kali Anda `git push` dari komputer, VPS bisa langsung di-update dengan `git pull`.

---

## BAGIAN 1 — Upload Project ke GitHub (dari Komputer Windows)

### 1️⃣ Install Git (jika belum)

Download dari https://git-scm.com/download/win lalu install.
Cek: buka PowerShell/CMD, ketik `git --version`

### 2️⃣ Buat Repository di GitHub

1. Login ke https://github.com
2. Klik tombol **+** (kanan atas) → **New repository**
3. Isi nama repo, misal: `redjaa-digital-bot`
4. Pilih **Private** (penting! karena ini bot dagang Anda)
5. **JANGAN** centang "Add README" (biar kosong dulu)
6. Klik **Create repository**

### 3️⃣ Inisialisasi Git di Project Lokal

Buka PowerShell/CMD di folder project:

```bash
cd "d:\Develop\Telegram\Bot\redjaa-digital"

git init
git add .
git commit -m "Initial commit - QuantumVault bot"
```

> ✅ Berkat `.gitignore`, file sensitif (`.env`, `data.json`, `qris.jpg`) TIDAK akan ikut ter-upload.

### 4️⃣ Hubungkan ke GitHub & Push

Ganti URL dengan URL repo Anda (terlihat di halaman GitHub):

```bash
git branch -M main
git remote add origin https://github.com/USERNAME/redjaa-digital-bot.git
git push -u origin main
```

Saat diminta login, gunakan **Personal Access Token** (bukan password biasa):

- GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Generate new token → centang scope **repo** → Generate
- Salin token, pakai sebagai password saat `git push`

---

## BAGIAN 2 — Clone ke VPS

### 1️⃣ Login ke VPS

```bash
ssh ubuntu@43.156.134.165
```

### 2️⃣ Clone Repository

Karena repo **private**, pakai token saat clone:

```bash
cd ~
git clone https://github.com/USERNAME/redjaa-digital-bot.git redjaa-digital
```

Masukkan username GitHub & token saat diminta.

> 💡 Agar tidak diminta token berulang kali, simpan kredensial:
>
> ```bash
> git config --global credential.helper store
> ```
>
> (token akan tersimpan setelah `git pull` pertama)

### 3️⃣ Siapkan File yang TIDAK Ada di Git

Karena `.env` dan `qris.jpg` tidak ikut ke GitHub, buat manual di VPS:

```bash
cd ~/redjaa-digital

# Buat .env (salin dari template lalu edit)
cp .env.example .env
nano .env      # isi dengan nilai asli, lalu Ctrl+O, Enter, Ctrl+X

# Upload qris.jpg dari komputer (jalankan di PowerShell Windows)
# scp "d:\Develop\Telegram\Bot\redjaa-digital\qris.jpg" ubuntu@43.156.134.165:/home/ubuntu/redjaa-digital/
```

### 4️⃣ Setup venv & Dependencies

```bash
cd ~/redjaa-digital
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5️⃣ Setup systemd (lihat DEPLOY_VPS.md langkah 7)

```bash
sudo cp ~/redjaa-digital/redjaa-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable redjaa-bot
sudo systemctl start redjaa-bot
```

---

## BAGIAN 3 — Workflow Update (Sehari-hari)

### Di Komputer Windows (setelah edit kode):

```bash
cd "d:\Develop\Telegram\Bot\redjaa-digital"
git add .
git commit -m "Deskripsi perubahan"
git push
```

### Di VPS (untuk menarik update):

```bash
cd ~/redjaa-digital
git pull
sudo systemctl restart redjaa-bot
```

Bot langsung jalan dengan kode terbaru! 🎉

---

## BAGIAN 4 (OPSIONAL) — Auto-Update dengan Satu Perintah

Buat script agar update di VPS cukup 1 perintah.

### Buat file `update.sh` di VPS:

```bash
nano ~/redjaa-digital/update.sh
```

Isi dengan:

```bash
#!/bin/bash
cd ~/redjaa-digital
echo "📥 Menarik update dari GitHub..."
git pull
echo "🔄 Restart bot..."
sudo systemctl restart redjaa-bot
echo "✅ Selesai! Status:"
sudo systemctl status redjaa-bot --no-pager -l | head -n 5
```

Simpan, lalu beri izin eksekusi:

```bash
chmod +x ~/redjaa-digital/update.sh
```

Sekarang setiap update cukup jalankan:

```bash
~/redjaa-digital/update.sh
```

---

## BAGIAN 5 (OPSIONAL LANJUTAN) — Auto-Deploy Otomatis dengan GitHub Actions

Kalau ingin VPS update **otomatis** setiap `git push` (tanpa perlu SSH manual), gunakan GitHub Actions + SSH.

### 1️⃣ Tambah Secret di GitHub

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Nama Secret   | Isi                                       |
| ------------- | ----------------------------------------- |
| `VPS_HOST`    | `43.156.134.165`                          |
| `VPS_USER`    | `ubuntu`                                  |
| `VPS_SSH_KEY` | isi private key SSH Anda (lihat di bawah) |

**Cara buat SSH key untuk deploy** (jalankan di VPS):

```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy -N ""
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/github_deploy    # salin SELURUH isi ini ke secret VPS_SSH_KEY
```

### 2️⃣ Buat Workflow File

Di komputer lokal, buat file `.github/workflows/deploy.yml`:

```yaml
name: Deploy to VPS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd ~/redjaa-digital
            git pull
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart redjaa-bot
```

### 3️⃣ Izinkan restart tanpa password

Agar `sudo systemctl restart` tidak minta password di GitHub Actions:

```bash
sudo visudo
```

Tambah baris di paling bawah (ganti `ubuntu` jika beda):

```
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart redjaa-bot
```

### 4️⃣ Push workflow-nya

```bash
git add .github/workflows/deploy.yml
git commit -m "Add auto-deploy workflow"
git push
```

Sekarang **setiap `git push` ke branch `main`**, VPS otomatis:

1. Tarik kode terbaru (`git pull`)
2. Update dependencies
3. Restart bot

Tanpa perlu SSH manual! 🚀

---

## 🔒 Catatan Keamanan Penting

1. **Repo HARUS Private** — kode bot dagang tidak boleh publik
2. **`.env` tidak pernah di-commit** — sudah dijaga `.gitignore`
3. **Backup `data.json`** sebelum update besar:
   ```bash
   cp ~/redjaa-digital/data.json ~/data-backup-$(date +%F).json
   ```
4. **Jika token pernah bocor**, regenerate di @BotFather & QuantumVault

---

## ❓ Troubleshooting

**`git pull` error "local changes would be overwritten":**

```bash
git stash        # simpan perubahan lokal sementara
git pull
git stash pop    # kembalikan (jika perlu)
```

**Lupa file mana yang berubah:**

```bash
git status
```

**Ingin batalkan semua perubahan lokal di VPS (pakai versi GitHub):**

```bash
git reset --hard origin/main
git pull
```

⚠️ Hati-hati, ini menghapus perubahan lokal yang belum di-commit.
