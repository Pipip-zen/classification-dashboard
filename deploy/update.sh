#!/usr/bin/env bash
# ==============================================================================
# Script: deploy/update.sh
# Deskripsi: Menarik kode terbaru dari git dan melakukan rolling update container
# ==============================================================================

set -e

echo "🔄 Menarik update terbaru dari GitHub (branch: main)..."
git pull origin main

echo "🏗️ Membangun ulang dan me-restart container Tactical GCS..."
docker compose up -d --build --remove-orphans

echo "🏥 Memeriksa status kesehatan sistem..."
sleep 5
curl -f http://localhost:8000/api/system/health || {
    echo "⚠️ Peringatan: Health check gagal. Silakan periksa log dengan 'docker compose logs -f'."
    exit 1
}

echo "✅ Update selesai! Tactical GCS beroperasi normal."
