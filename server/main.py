"""
Module: server/main.py
Deskripsi:
    Aplikasi utama FastAPI untuk Ground Control Station (GCS) Taktis:
    - Menyajikan API RESTful & WebSocket Telemetri
    - Menghubungkan video pipeline MJPEG berlatensi rendah
    - Menyajikan antarmuka statis React SPA (frontend/dist) pada port tunggal
"""

import sys
import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

# Tambahkan direktori root projek ke sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.state import state
from server.services.stream_worker import stream_worker
from server.routes.stream import router as stream_router
from server.routes.analysis import router as analysis_router
from server.routes.stitching import router as stitching_router
from server.routes.inpainting import router as inpainting_router
from server.routes.dataset import router as dataset_router
from server.routes.system import router as system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Daftarkan event loop ke stream worker
    loop = asyncio.get_running_loop()
    stream_worker.set_event_loop(loop)
    print(f"[STARTUP] Tactical GCS Core Online. Weights: {state.model_path}")
    yield
    # Shutdown: Bersihkan resources
    print("[SHUTDOWN] Menghentikan stream worker & melepaskan resources...")
    stream_worker.stop_stream()


app = FastAPI(
    title="Tactical AI Reconnaissance & Combat GCS",
    description="Ground Control Station Terpadu untuk Wahana ROV Danau & Drone Spectator",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware (Untuk kemudahan debug Vite di port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrasi Router API
app.include_router(stream_router)
app.include_router(analysis_router)
app.include_router(stitching_router)
app.include_router(inpainting_router)
app.include_router(dataset_router)
app.include_router(system_router)


# WebSocket Telemetri Real-time
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    await state.register_ws(websocket)
    
    # Kirim state telemetri awal segera setelah koneksi dibuka
    try:
        await websocket.send_json(state.latest_telemetry)
    except Exception:
        pass

    try:
        while True:
            # Dengarkan pesan atau heartbeat dari frontend
            data = await websocket.receive_text()
            # Jika frontend mengirim request update config via WS
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        state.unregister_ws(websocket)
    except Exception:
        state.unregister_ws(websocket)


# Mount Static Files Frontend (Single-Port Hosting)
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Mount assets folder
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_root():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"status": "GCS Online", "docs": "/docs"}

    # SPA Fallback: semua route selain /api dan /ws diarahkan ke index.html
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
            "health": "/api/system/health"
        }
