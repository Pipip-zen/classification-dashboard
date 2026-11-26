#!/usr/bin/env bash
# ==============================================================================
# Script: deploy/update.sh
# Deskripsi: Menarik kode terbaru dari git dan melakukan rolling update container
# ==============================================================================

set -e

echo "🔄 Menarik update terbaru dari GitHub (branch: main)..."
git pull origin main

echo "🏗️ Membangun ulang dan me-restart container Tactical GCS..."
if docker compose version >/dev/null 2>&1; then
    docker compose up -d --build --remove-orphans
else
    docker-compose up -d --build --remove-orphans
fi

echo "🏥 Memeriksa status kesehatan sistem..."
for i in $(seq 1 12); do
    if curl -fsS http://localhost:8000/api/system/health >/dev/null 2>&1; then
        echo "✅ Update selesai! Tactical GCS beroperasi normal."
        exit 0
    fi
    sleep 3
done

echo "⚠️ Peringatan: Health check gagal setelah 36 detik. Silakan periksa log container."
exit 1
