# ==============================================================================
# STAGE 1: Frontend Builder (React 19 + TypeScript + Vite)
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy dependensi package
COPY frontend/package*.json ./
RUN npm install

# Copy seluruh source code frontend dan build aset statis
COPY frontend/ ./
RUN npm run build

# ==============================================================================
# STAGE 2: Backend Runtime (Python 3.11 Slim + OpenCV + PyTorch + FastAPI)
# ==============================================================================
FROM python:3.11-slim AS runner

# Environment variables produksi
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    HOST=0.0.0.0 \
    NO_BROWSER=1

WORKDIR /app

# Install dependensi sistem untuk OpenCV headless, FFmpeg, dan network utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU wheel lebih dulu agar Docker tidak mengunduh paket CUDA ~3-4 GB
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
COPY requirements.txt ./
RUN pip install --no-cache-dir torch torchvision --index-url ${TORCH_INDEX_URL} && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code backend, model bobot AI, dan dataset testbench
COPY core/ ./core/
COPY server/ ./server/
COPY models/ ./models/
COPY data/ ./data/
COPY testbench_samples/ ./testbench_samples/
COPY scripts/ ./scripts/
COPY run.py ./

# Salin aset frontend hasil build dari Stage 1 (Single-Port GCS)
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port HTTP / WebSocket GCS
EXPOSE 8000

# Health check otomatis untuk Docker & orchestrator (Swarm / K8s / Dokku)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/system/health || exit 1

# Jalankan server FastAPI via Uvicorn
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
