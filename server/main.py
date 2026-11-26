"""
Module: server/main.py
Deskripsi:
    Aplikasi utama FastAPI untuk Ground Control Station (GCS) Taktis Multi-Channel:
    - Otentikasi & RBAC 3 Peran (Admin Drone, Admin ROV, Spectator)
    - API RESTful & WebSocket Telemetri per channel (/ws/telemetry/{channel_id})
    - WebSocket Push Ingest untuk browser Operator (/ws/ingest/{channel_id})
    - WebSocket Binary Viewer untuk Spectator (/ws/view/{channel_id})
    - Hosting statis React SPA (frontend/dist) pada port tunggal
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.state import state, VALID_CHANNELS
from server.auth import verify_token, can_view_channel
from server.services.stream_worker import stream_worker
from server.routes.auth import router as auth_router
from server.routes.stream import router as stream_router
from server.routes.analysis import router as analysis_router
from server.routes.stitching import router as stitching_router
from server.routes.inpainting import router as inpainting_router
from server.routes.dataset import router as dataset_router
from server.routes.system import router as system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    stream_worker.set_event_loop(loop)
    print(f"[STARTUP] Tactical GCS Multi-Channel Online. Weights: {state.model_path}")
    yield
    print("[SHUTDOWN] Menghentikan seluruh channel worker & melepaskan resources...")
    stream_worker.stop_all()


app = FastAPI(
    title="VANGUARD AI — Ground Control Station",
    description="VANGUARD AI: Role-Based Multi-Channel Drone & ROV Tactical Reconnaissance GCS",
    version="3.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(stream_router)
app.include_router(analysis_router)
app.include_router(stitching_router)
app.include_router(inpainting_router)
app.include_router(dataset_router)
app.include_router(system_router)


async def _authenticate_ws(websocket: WebSocket, token: Optional[str]) -> Optional[Dict[str, Any]]:
    user = verify_token(token)
    if user is None:
        await websocket.close(code=4001)
        return None
    return user


async def _serve_telemetry_ws(websocket: WebSocket, channel_id: Optional[str] = None):
    await websocket.accept()
    await state.register_ws(websocket, channel_id=channel_id)

    try:
        ch = state.get_channel(channel_id)
        await websocket.send_json(ch.latest_telemetry)
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, Exception):
        state.unregister_ws(websocket, channel_id=channel_id)


@app.websocket("/ws/telemetry")
async def websocket_legacy_telemetry(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    user = await _authenticate_ws(websocket, token)
    if user is None:
        return
    target = user["role"] if user["role"] in VALID_CHANNELS else None
    await _serve_telemetry_ws(websocket, channel_id=target)


@app.websocket("/ws/telemetry/{channel_id}")
async def websocket_channel_telemetry(
    websocket: WebSocket,
    channel_id: str,
    token: Optional[str] = Query(default=None),
):
    cid = channel_id.lower()
    if cid not in VALID_CHANNELS:
        await websocket.close(code=4004)
        return
    user = await _authenticate_ws(websocket, token)
    if user is None:
        return
    if not can_view_channel(cid, user):
        await websocket.close(code=4003)
        return
    await _serve_telemetry_ws(websocket, channel_id=cid)


@app.websocket("/ws/ingest/{channel_id}")
async def websocket_browser_ingest(
    websocket: WebSocket,
    channel_id: str,
    token: Optional[str] = Query(default=None),
    session_id: str = Query(default=""),
    source_label: str = Query(default="Browser Window Capture"),
    pin: Optional[str] = Query(default=None),
):
    """Menerima frame JPEG biner khusus pemilik peran channel dan membalas telemetri."""
    cid = channel_id.lower()
    if cid not in VALID_CHANNELS:
        await websocket.close(code=4004)
        return

    user = await _authenticate_ws(websocket, token)
    if user is None:
        return
    if user["role"] != cid:
        await websocket.close(code=4003)
        return

    await websocket.accept()
    ch = state.get_channel(cid)
    worker = stream_worker.get_worker(cid)

    sid = session_id or f"ws-{id(websocket)}"
    owner_display = f"{user['display_name']} ({source_label})"
    ok, msg = ch.claim(session_id=sid, owner_label=owner_display, pin=pin, operator_pin=state.operator_pin)
    if not ok:
        try:
            await websocket.send_json({"type": "lock_rejected", "error": msg, "owner_label": ch.owner_label})
        except Exception:
            pass
        await websocket.close(code=4003)
        return

    worker.start_browser_ingest(source_label=source_label)

    try:
        await websocket.send_json({"type": "ingest_ready", "channel_id": cid, "telemetry": ch.latest_telemetry})
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            raw_bytes = message.get("bytes")
            if raw_bytes:
                ch.heartbeat(sid)
                await asyncio.to_thread(worker.push_browser_frame, raw_bytes)
                await websocket.send_json({"type": "telemetry", "telemetry": ch.latest_telemetry})
                continue

            raw_text = message.get("text")
            if raw_text:
                if raw_text == "ping":
                    ch.heartbeat(sid)
                    await websocket.send_text("pong")
                    continue
                try:
                    cmd = json.loads(raw_text)
                    if cmd.get("type") == "source_label" and cmd.get("label"):
                        ch.source_param = str(cmd["label"])
                except Exception:
                    pass
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if ch.owner_session_id == sid:
            worker.stop_stream()
            ch.release(sid)


@app.websocket("/ws/view/{channel_id}")
async def websocket_spectator_view(
    websocket: WebSocket,
    channel_id: str,
    token: Optional[str] = Query(default=None),
    mode: str = Query(default="main"),
):
    """Mengirim frame JPEG teranotasi secara kontinyu untuk Viewer berhak akses."""
    cid = channel_id.lower()
    if cid not in VALID_CHANNELS:
        await websocket.close(code=4004)
        return

    user = await _authenticate_ws(websocket, token)
    if user is None:
        return
    if not can_view_channel(cid, user):
        await websocket.close(code=4003)
        return

    await websocket.accept()
    worker = stream_worker.get_worker(cid)
    is_pip = mode.lower() == "pip"
    min_interval = 0.22 if is_pip else 0.03
    last_seq = -1
    last_sent_at = 0.0

    async def _send_frames():
        nonlocal last_seq, last_sent_at
        while True:
            now = time.monotonic()
            if worker.frame_seq != last_seq and (now - last_sent_at) >= min_interval:
                frame_bytes = worker.get_latest_frame(pip=is_pip)
                last_seq = worker.frame_seq
                last_sent_at = now
                await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(0.02)

    async def _watch_disconnect():
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break

    send_task = asyncio.create_task(_send_frames())
    recv_task = asyncio.create_task(_watch_disconnect())
    try:
        _, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except (WebSocketDisconnect, Exception):
        send_task.cancel()
        recv_task.cancel()


FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_root():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"status": "GCS Online", "docs": "/docs"}

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"error": "Page not found"}
else:
    @app.get("/")
    def index_fallback():
        return {
            "message": "Tactical GCS API Active. Frontend belum di-build. Jalankan 'npm run build' di folder frontend atau akses /api/system/health.",
            "docs": "/docs",
            "health": "/api/system/health",
        }
