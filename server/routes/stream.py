"""
Module: server/routes/stream.py
Deskripsi:
    Router FastAPI untuk streaming MJPEG video, kontrol sumber input, dan konfigurasi AI.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.state import state
from server.services.stream_worker import stream_worker
from core.stream_capture import StreamCapture

router = APIRouter(prefix="/api/stream", tags=["Stream"])


class StreamStartRequest(BaseModel):
    source_type: str  # 'testbench', 'youtube', 'screen', 'network', 'webcam', 'tiktok'
    source_param: str


class StreamConfigRequest(BaseModel):
    cockpit_mode: Optional[str] = None
    confidence_gate: Optional[float] = None
    dusk_enhancer: Optional[bool] = None
    reticle_visible: Optional[bool] = None
    labels_visible: Optional[bool] = None
    compact_hud: Optional[bool] = None


async def frame_generator():
    """Generator untuk streaming multipart JPEG ke browser."""
    while True:
        frame_bytes = stream_worker.get_latest_frame()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        await asyncio.sleep(0.033)  # ~30 FPS


@router.get("/feed")
def get_video_feed():
    """Endpoint MJPEG video streaming."""
    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/start")
def start_stream(req: StreamStartRequest):
    """Memulai atau beralih sumber video stream."""
    res = stream_worker.start_stream(req.source_type, req.source_param)
    return res


@router.post("/stop")
def stop_stream():
    """Menghentikan streaming."""
    stream_worker.stop_stream()
    return {"success": True, "message": "Stream stopped"}


@router.post("/config")
def update_config(req: StreamConfigRequest):
    """Memperbarui parameter AI dan HUD secara dinamis."""
    updates = req.model_dump(exclude_unset=True)
    state.update_config(**updates)
    return {
        "success": True,
        "config": {
            "cockpit_mode": state.cockpit_mode,
            "confidence_gate": state.confidence_gate,
            "dusk_enhancer": state.dusk_enhancer,
            "reticle_visible": state.reticle_visible,
            "labels_visible": state.labels_visible,
            "compact_hud": state.compact_hud,
        }
    }


@router.get("/status")
def get_status():
    """Mengambil status streaming dan konfigurasi terkini."""
    return {
        "stream_active": state.stream_active,
        "source_type": state.source_type,
        "source_param": state.source_param,
        "cockpit_mode": state.cockpit_mode,
        "confidence_gate": state.confidence_gate,
        "dusk_enhancer": state.dusk_enhancer,
        "fps": state.current_fps,
        "latency_ms": state.last_latency_ms,
        "telemetry": state.latest_telemetry
    }


@router.get("/sources")
def get_available_sources():
    """Mengambil daftar sumber input yang tersedia di sistem."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    video_dir = base_dir / "testbench_samples" / "videos"
    
    testbench_vids = []
    if video_dir.exists():
        for p in video_dir.glob("*.mp4"):
            n = p.name
            desc = n
            if "forest" in n.lower():
                desc = f"🌲 {n} (Drone Hutan & Pejalan Kaki)"
            elif "land" in n.lower() or "drone" in n.lower():
                desc = f"🚁 {n} (Drone Perkotaan & Jalan Raya)"
            elif "rov" in n.lower() or "underwater" in n.lower():
                desc = f"🔵 {n} (ROV Danau & Bawah Air)"
            testbench_vids.append({
                "filename": n,
                "display_name": desc,
                "size_mb": round(p.stat().st_size / (1024 * 1024), 2)
            })

    # Cek jendela aktif untuk Screen Mirroring
    active_windows = []
    try:
        import pygetwindow as gw
        active_windows = [w.title for w in gw.getAllWindows() if w.title.strip() != ""]
    except Exception:
        active_windows = []

    return {
        "testbench_videos": testbench_vids,
        "active_windows": active_windows,
        "default_drone_video": "drone_forest_person_patrol.mp4",
        "default_rov_video": "rov_underwater_patrol.mp4"
    }
