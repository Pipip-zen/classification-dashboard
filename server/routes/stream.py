"""
Module: server/routes/stream.py
Deskripsi:
    Router FastAPI multi-channel ('drone' dan 'rov') dengan pengaman otorisasi RBAC:
    - Kendali stream, config, lock, dan kalibrasi kompas khusus pemilik peran channel
    - Monitoring feed dan status terbuka untuk Spectator serta pemilik channel
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.state import state, ChannelState, VALID_CHANNELS
from server.services.stream_worker import stream_worker
from server.auth import (
    get_current_user,
    require_operator_role,
    ensure_channel_operator,
    can_view_channel,
)

router = APIRouter(tags=["Stream & Channels"])


class StreamStartRequest(BaseModel):
    source_type: str
    source_param: str
    session_id: Optional[str] = None


class StreamStopRequest(BaseModel):
    session_id: Optional[str] = None


class StreamConfigRequest(BaseModel):
    cockpit_mode: Optional[str] = None
    confidence_gate: Optional[float] = None
    dusk_enhancer: Optional[bool] = None
    reticle_visible: Optional[bool] = None
    labels_visible: Optional[bool] = None
    compact_hud: Optional[bool] = None


class CompassCalibrateRequest(BaseModel):
    action: str = "set_north"
    offset_deg: Optional[float] = 0.0


class ChannelClaimRequest(BaseModel):
    session_id: str
    owner_label: Optional[str] = None
    pin: Optional[str] = None


class ChannelSessionRequest(BaseModel):
    session_id: Optional[str] = None


def _get_valid_channel(channel_id: str) -> ChannelState:
    cid = channel_id.lower()
    if cid not in VALID_CHANNELS:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' tidak valid. Gunakan 'drone' atau 'rov'.")
    return state.get_channel(cid)


async def _frame_generator(channel_id: str):
    """Generator multipart JPEG untuk satu channel."""
    worker = stream_worker.get_worker(channel_id)
    while True:
        frame_bytes = worker.get_latest_frame()
        if frame_bytes:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        await asyncio.sleep(0.033)


def _start_channel_impl(channel_id: str, req: StreamStartRequest) -> Dict[str, Any]:
    ch = _get_valid_channel(channel_id)
    if req.session_id and ch.is_locked_by_other(req.session_id):
        return {
            "success": False,
            "locked": True,
            "error": f"Channel dikunci oleh {ch.owner_label or 'Operator lain'}",
        }
    if req.session_id:
        ch.claim(req.session_id, operator_pin=state.operator_pin)
    return stream_worker.start_stream(req.source_type, req.source_param, channel_id=channel_id)


def _stop_channel_impl(channel_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    ch = _get_valid_channel(channel_id)
    if session_id and ch.is_locked_by_other(session_id):
        return {
            "success": False,
            "locked": True,
            "error": f"Channel dikunci oleh {ch.owner_label or 'Operator lain'}",
        }
    stream_worker.stop_stream(channel_id=channel_id)
    return {"success": True, "channel_id": channel_id, "message": "Stream stopped"}


def _update_config_impl(channel_id: str, req: StreamConfigRequest) -> Dict[str, Any]:
    ch = _get_valid_channel(channel_id)
    updates = req.model_dump(exclude_unset=True)
    ch.update_config(**updates)
    return {
        "success": True,
        "channel_id": ch.channel_id,
        "config": {
            "cockpit_mode": ch.channel_id,
            "confidence_gate": ch.confidence_gate,
            "dusk_enhancer": ch.dusk_enhancer,
            "reticle_visible": ch.reticle_visible,
            "labels_visible": ch.labels_visible,
            "compact_hud": ch.compact_hud,
        },
    }


def _calibrate_compass_impl(channel_id: str, req: CompassCalibrateRequest) -> Dict[str, Any]:
    ch = _get_valid_channel(channel_id)
    if req.action == "set_north":
        new_hdg = ch.orientation_estimator.set_north()
    elif req.action == "set_offset" and req.offset_deg is not None:
        new_hdg = ch.orientation_estimator.set_heading(req.offset_deg)
    elif req.action == "reset":
        ch.orientation_estimator.reset()
        new_hdg = ch.orientation_estimator.current_heading_deg
    else:
        new_hdg = ch.orientation_estimator.current_heading_deg

    cardinal = ch.orientation_estimator.deg_to_cardinal(new_hdg)
    with ch.lock:
        ch.latest_telemetry = {
            **ch.latest_telemetry,
            "heading_deg": round(new_hdg, 1),
            "cardinal": cardinal,
            "compass_calibrated": ch.orientation_estimator.is_calibrated,
        }

    return {
        "success": True,
        "channel_id": ch.channel_id,
        "action": req.action,
        "heading_deg": round(new_hdg, 1),
        "cardinal": cardinal,
        "is_calibrated": ch.orientation_estimator.is_calibrated,
    }


# ==============================================================================
# Multi-Channel Routes (/api/channels/...)
# ==============================================================================


@router.get("/api/channels/status")
def get_all_channels_status(user: Dict[str, Any] = Depends(get_current_user)):
    """Mengambil ringkasan live channel yang boleh diakses sesuai peran user."""
    return {
        "channels": {
            cid: state.get_channel(cid).status_summary()
            for cid in VALID_CHANNELS
            if can_view_channel(cid, user)
        }
    }


@router.post("/api/channels/{channel_id}/claim")
def claim_channel(
    channel_id: str,
    req: ChannelClaimRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Mengklaim hak kontrol Operator pada channel milik perannya."""
    ch = _get_valid_channel(channel_id)
    ensure_channel_operator(ch.channel_id, user)
    ok, msg = ch.claim(
        session_id=req.session_id,
        owner_label=req.owner_label or user["display_name"],
        pin=req.pin,
        operator_pin=state.operator_pin,
    )
    return {
        "success": ok,
        "locked": not ok,
        "message": msg,
        "channel": ch.status_summary(),
    }


@router.post("/api/channels/{channel_id}/release")
def release_channel(
    channel_id: str,
    req: Optional[ChannelSessionRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Melepaskan kunci akses Operator dan menghentikan stream channel tersebut."""
    ch = _get_valid_channel(channel_id)
    ensure_channel_operator(ch.channel_id, user)
    sid = req.session_id if req else None
    released = ch.release(sid)
    if released:
        stream_worker.stop_stream(channel_id=ch.channel_id)
    return {"success": released, "channel_id": ch.channel_id}


@router.post("/api/channels/{channel_id}/heartbeat")
def heartbeat_channel(
    channel_id: str,
    req: ChannelClaimRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Memperpanjang masa aktif lock tab Operator agar tidak expired."""
    ch = _get_valid_channel(channel_id)
    ensure_channel_operator(ch.channel_id, user)
    ok = ch.heartbeat(req.session_id)
    return {"success": ok, "channel_id": ch.channel_id}


@router.get("/api/channels/{channel_id}/feed")
def get_channel_feed(channel_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    ch = _get_valid_channel(channel_id)
    if not can_view_channel(ch.channel_id, user):
        raise HTTPException(status_code=403, detail="Akses ditolak untuk melihat channel ini.")
    return StreamingResponse(
        _frame_generator(ch.channel_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/api/channels/{channel_id}/start")
def start_channel_stream(
    channel_id: str,
    req: StreamStartRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    ch = _get_valid_channel(channel_id)
    ensure_channel_operator(ch.channel_id, user)
    return _start_channel_impl(ch.channel_id, req)


@router.post("/api/channels/{channel_id}/stop")
def stop_channel_stream(
    channel_id: str,
    req: Optional[StreamStopRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
):
    ch = _get_valid_channel(channel_id)
    ensure_channel_operator(ch.channel_id, user)
    return _stop_channel_impl(ch.channel_id, req.session_id if req else None)


@router.post("/api/channels/{channel_id}/config")
def update_channel_config(
    channel_id: str,
    req: StreamConfigRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    ch = _get_valid_channel(channel_id)
    ensure_channel_operator(ch.channel_id, user)
    return _update_config_impl(ch.channel_id, req)


@router.post("/api/channels/{channel_id}/compass/calibrate")
def calibrate_channel_compass(
    channel_id: str,
    req: CompassCalibrateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    ch = _get_valid_channel(channel_id)
    ensure_channel_operator(ch.channel_id, user)
    return _calibrate_compass_impl(ch.channel_id, req)


# ==============================================================================
# Legacy Single-Channel Routes (/api/stream/...) dengan Guard Peran
# ==============================================================================


@router.get("/api/stream/feed")
def get_video_feed(user: Dict[str, Any] = Depends(get_current_user)):
    target = user["role"] if user["role"] in VALID_CHANNELS else state.active_channel_id
    return StreamingResponse(
        _frame_generator(target),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/api/stream/start")
def start_stream(req: StreamStartRequest, user: Dict[str, Any] = Depends(require_operator_role)):
    target = user["role"]
    state.active_channel_id = target
    return _start_channel_impl(target, req)


@router.post("/api/stream/stop")
def stop_stream(user: Dict[str, Any] = Depends(require_operator_role)):
    target = user["role"]
    return _stop_channel_impl(target)


@router.post("/api/stream/config")
def update_config(req: StreamConfigRequest, user: Dict[str, Any] = Depends(require_operator_role)):
    if req.cockpit_mode in VALID_CHANNELS:
        ensure_channel_operator(req.cockpit_mode, user)
    target = user["role"]
    state.active_channel_id = target
    return _update_config_impl(target, req)


@router.post("/api/stream/compass/calibrate")
def calibrate_compass(req: CompassCalibrateRequest, user: Dict[str, Any] = Depends(require_operator_role)):
    target = user["role"]
    return _calibrate_compass_impl(target, req)


@router.get("/api/stream/status")
def get_status(user: Dict[str, Any] = Depends(get_current_user)):
    target = user["role"] if user["role"] in VALID_CHANNELS else state.active_channel_id
    ch = state.get_channel(target)
    return {
        "stream_active": ch.stream_active,
        "source_type": ch.source_type,
        "source_param": ch.source_param,
        "cockpit_mode": ch.channel_id,
        "confidence_gate": ch.confidence_gate,
        "dusk_enhancer": ch.dusk_enhancer,
        "fps": ch.current_fps,
        "ai_fps": ch.ai_fps,
        "latency_ms": ch.last_latency_ms,
        "telemetry": ch.latest_telemetry,
    }


@router.get("/api/stream/sources", dependencies=[Depends(require_operator_role)])
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
                desc = f"{n} (Drone Hutan & Pejalan Kaki)"
            elif "land" in n.lower() or "drone" in n.lower():
                desc = f"{n} (Drone Perkotaan & Jalan Raya)"
            elif "rov" in n.lower() or "underwater" in n.lower():
                desc = f"{n} (ROV Danau & Bawah Air)"
            testbench_vids.append({
                "filename": n,
                "display_name": desc,
                "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
            })

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
        "default_rov_video": "rov_underwater_patrol.mp4",
    }
