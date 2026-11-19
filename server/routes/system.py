"""
Module: server/routes/system.py
Deskripsi:
    Router FastAPI untuk pemantauan kesehatan sistem, hardware GPU CUDA, dan reload AI core.
"""

import sys
import torch
import cv2
from pathlib import Path
from fastapi import APIRouter

from server.state import state

router = APIRouter(prefix="/api/system", tags=["System & Hardware"])


@router.get("/health")
def get_system_health():
    """Mengambil status kesehatan sistem dan hardware akselerasi GPU."""
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU (No CUDA)"
    
    return {
        "status": "OPERATIONAL",
        "ai_model": {
            "model_path": state.model_path,
            "weights_exist": Path(state.model_path).exists(),
            "device": "cuda:0" if cuda_available else "cpu",
            "device_name": device_name,
            "cuda_available": cuda_available
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "opencv_version": cv2.__version__
        },
        "streaming": {
            "active": state.stream_active,
            "source_type": state.source_type,
            "source_param": state.source_param,
            "cockpit_mode": state.cockpit_mode,
            "fps": state.current_fps,
            "latency_ms": state.last_latency_ms
        }
    }


@router.post("/reload-model")
def reload_model():
    """Memuat ulang model YOLOv8 (models/best.pt)."""
    ok = state.reload_detector()
    return {
        "success": ok,
        "model_path": state.model_path,
        "message": "Model berhasil dimuat ulang ke memori GPU" if ok else "Gagal memuat ulang model"
    }
