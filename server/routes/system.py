"""
Module: server/routes/system.py
Deskripsi:
    Router FastAPI untuk pemantauan kesehatan sistem, hardware GPU CUDA, status channel, dan reload AI core.
"""

import sys
import torch
import cv2
from pathlib import Path
from fastapi import APIRouter, Depends

from server.state import state, VALID_CHANNELS
from server.auth import require_operator_role

router = APIRouter(prefix="/api/system", tags=["System & Hardware"])


@router.get("/health")
def get_system_health():
    """Mengambil status kesehatan sistem, hardware akselerasi, dan ringkasan multi-channel."""
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU (No CUDA)"

    return {
        "status": "OPERATIONAL",
        "ai_model": {
            "model_path": state.model_path,
            "weights_exist": Path(state.model_path).exists(),
            "device": "cuda:0" if cuda_available else "cpu",
            "device_name": device_name,
            "cuda_available": cuda_available,
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "opencv_version": cv2.__version__,
        },
        "streaming": {
            "active": state.stream_active,
            "source_type": state.source_type,
            "source_param": state.source_param,
            "cockpit_mode": state.cockpit_mode,
            "fps": state.current_fps,
            "latency_ms": state.last_latency_ms,
        },
        "channels": {
            cid: state.get_channel(cid).status_summary() for cid in VALID_CHANNELS
        },
    }


@router.post("/reload-model", dependencies=[Depends(require_operator_role)])
def reload_model():
    """Memuat ulang model YOLOv8 (models/best.pt)."""
    ok = state.reload_detector()
    return {
        "success": ok,
        "model_path": state.model_path,
        "message": "Model berhasil dimuat ulang" if ok else "Gagal memuat ulang model",
    }
