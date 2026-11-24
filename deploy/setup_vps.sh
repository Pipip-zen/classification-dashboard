#!/usr/bin/env bash
# ==============================================================================
# Script: deploy/setup_vps.sh
# Deskripsi: Setup otomatis VPS (Ubuntu/Debian) untuk Tactical AI GCS
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 MEMULAI SETUP VPS TACTICAL AI GROUND CONTROL STATION"
echo "=========================================================="

# 1. Update sistem paket
echo "[1/5] Memperbarui indeks paket sistem..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Pasang dependensi esensial (Docker, Git, Curl, UFW)
echo "[2/5] Memeriksa dan memasang Docker Engine & UFW..."
if ! command -v docker &> /dev/null; then
    echo "Docker belum terpasang. Mengunduh installer resmi Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm -f get-docker.sh
    sudo usermod -aG docker "$USER"
    echo "Docker berhasil dipasang."
else
    echo "Docker sudah terpasang."
fi

sudo apt-get install -y git curl ufw docker-compose-plugin

# 3. Konfigurasi Firewall UFW
echo "[3/5] Mengatur firewall (UFW)..."
sudo ufw allow 22/tcp comment "SSH"
sudo ufw allow 80/tcp comment "HTTP Web"
sudo ufw allow 443/tcp comment "HTTPS SSL"
sudo ufw allow 8000/tcp comment "FastAPI Tactical GCS"
sudo ufw allow 5602/udp comment "ROV / Drone SDP Stream"
sudo ufw --force enable

# 4. Inisialisasi Environment
echo "[4/5] Mempersiapkan file environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "File .env berhasil dibuat dari .env.example."
fi

# 5. Jalankan Container
echo "[5/5] Membangun dan menjalankan Tactical GCS container..."
docker compose up -d --build

echo ""
echo "=========================================================="
echo "✅ TACTICAL GCS BERHASIL BERJALAN DI VPS!"
echo "🌐 Akses antarmuka: http://$(curl -s ifconfig.me):8000"
echo "📖 Cek log container: docker compose logs -f"
echo "=========================================================="
