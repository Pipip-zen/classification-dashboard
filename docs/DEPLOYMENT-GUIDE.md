# PANDUAN DEPLOYMENT KE VPS & OTOMASI CI/CD
**Proyek:** Tactical AI Ground Control Station (GCS)  
**Arsitektur:** Docker Multi-Stage (Vite React + FastAPI Python 3.11)  
**Target OS:** Ubuntu 22.04 / 24.04 LTS atau Debian 12  

---

## 1. Arsitektur Deployment & Alur CI/CD

```mermaid
flowchart LR
    A["Developer (Git Push main)"] --> B["GitHub Actions CI"]
    B --> C["1. Build Frontend (Vite)"]
    C --> D["2. Test Unit & API (8/8 Modul)"]
    D --> E["3. Build Check Docker Image"]
    E --> F{"Semua Test Lolos?"}
    F -->|Ya| G["GitHub Actions CD (SSH)"]
    F -->|Tidak| H["Kirim Notifikasi Fail"]
    G --> I["VPS Server (Ubuntu)"]
    I --> J["docker compose up -d --build"]
    J --> K["Akses Web GCS Port 8000 / 80 / 443"]
```

---

## 2. Persyaratan Spesifikasi VPS

* **OS:** Ubuntu 22.04 LTS / 24.04 LTS (64-bit)
* **CPU:** Minimal 2 vCPU (Rekomendasi: 4 vCPU untuk video inference lancar)
* **RAM:** Minimal 2 GB RAM (Rekomendasi: 4 GB RAM + 2 GB Swap)
* **Disk:** Minimal 15 GB SSD / NVMe
* **Port yang harus dibuka (Firewall/Security Group):**
  * `22/tcp` — Akses SSH VPS
  * `80/tcp` — HTTP Web (Nginx / Let's Encrypt)
  * `443/tcp` — HTTPS Web (SSL)
  * `8000/tcp` — Tactical GCS API & Single-Port Web Dashboard
  * `5602/udp` — Video Stream Protokol SDP/RTP dari wahana ROV / Drone

---

## 3. Langkah Instalasi Cepat di VPS (One-Click Setup)

### Langkah 3.1: Hubungkan ke VPS via SSH
```bash
ssh ubuntu@IP_VPS_ANDA
```

### Langkah 3.2: Clone Repository ke Direktori `/opt/tactical-gcs`
```bash
sudo git clone https://github.com/Pipip-zen/classification-dashboard.git /opt/tactical-gcs
sudo chown -R $USER:$USER /opt/tactical-gcs
cd /opt/tactical-gcs
```

### Langkah 3.3: Jalankan Skrip Setup Otomatis
```bash
chmod +x deploy/setup_vps.sh deploy/update.sh
./deploy/setup_vps.sh
```

Skrip ini akan secara otomatis:
1. Meng-update paket sistem Ubuntu.
2. Memasang Docker Engine resmi & Docker Compose plugin.
3. Mengonfigurasi firewall `ufw` untuk port 22, 80, 443, 8000, dan 5602.
4. Membuat file `.env` dari `.env.example`.
5. Membangun multi-stage Docker image dan menjalankan container GCS di background.

Setelah selesai, antarmuka Tactical GCS langsung aktif di:
`http://IP_VPS_ANDA:8000`

---

## 4. Konfigurasi CI/CD Otomatis (GitHub Actions)

Agar setiap kali Anda melakukan `git push origin main` kode otomatis teruji dan ter-deploy ke VPS tanpa perlu login SSH manual:

### Langkah 4.1: Buat SSH Key Khusus Deployment di VPS
Di terminal VPS Anda, buat pasangan SSH key baru:
```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy -N ""
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Tampilkan private key untuk disalin ke GitHub:
```bash
cat ~/.ssh/github_deploy
```
*(Salin seluruh teks mulai dari `-----BEGIN OPENSSH PRIVATE KEY-----` sampai `-----END OPENSSH PRIVATE KEY-----`)*

### Langkah 4.2: Daftarkan Secrets di Repository GitHub
1. Buka repo GitHub: `https://github.com/Pipip-zen/classification-dashboard`
2. Klik tab **Settings** -> **Secrets and variables** -> **Actions**
3. Klik tombol **New repository secret** dan masukkan 4 konfigurasi berikut:

| Nama Secret | Nilai / Contoh | Keterangan |
| :--- | :--- | :--- |
| `VPS_HOST` | `103.xxx.xxx.xxx` atau `domain.com` | Alamat IP Publik VPS Anda |
| `VPS_USERNAME` | `ubuntu` atau `root` | Username SSH login VPS |
| `VPS_SSH_KEY` | *(Teks private key `~/.ssh/github_deploy`)* | Kunci otentikasi SSH tanpa password |
| `VPS_PORT` | `22` | Port SSH (default: 22) |
| `VPS_PROJECT_DIR` | `/opt/tactical-gcs` | Lokasi folder clone di VPS |

Setelah tersimpan, alur CI/CD otomatis berjalan di setiap `git push origin main`.

---

## 5. Menjalankan Nginx Reverse Proxy & SSL HTTPS (Domain Sendiri)

Jika Anda ingin mengakses dashboard menggunakan nama domain (misal: `https://gcs.domainanda.com`):

1. Arahkan DNS **A Record** `gcs.domainanda.com` ke IP Publik VPS Anda.
2. Edit file `deploy/nginx/nginx.conf` dan ubah `server_name _;` menjadi:
   ```nginx
   server_name gcs.domainanda.com;
   ```
3. Pasang sertifikat SSL gratis via Certbot di VPS:
   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d gcs.domainanda.com
   ```
4. Atau gunakan `docker-compose.prod.yml` untuk stack Nginx + GCS terpadu:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

---

## 6. Perintah Pemeliharaan & Troubleshooting

* **Melihat Log Real-time:**
  ```bash
  docker compose logs -f
  ```
* **Restart Service:**
  ```bash
  docker compose restart
  ```
* **Update Manual (Bila Tidak Menggunakan CI/CD):**
  ```bash
  ./deploy/update.sh
  ```
* **Cek Health Check API:**
  ```bash
  curl http://localhost:8000/api/system/health
  ```
* **Hentikan Container:**
  ```bash
  docker compose down
  ```
