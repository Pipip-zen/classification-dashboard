"""
Launcher Tunggal: Tactical AI Ground Control Station (GCS)
Menjalankan server FastAPI pada port 8000 yang menyajikan API & Web Frontend React secara terpadu.
"""

import sys
import os
import subprocess
import webbrowser
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def check_frontend_build():
    dist_dir = BASE_DIR / "frontend" / "dist"
    index_file = dist_dir / "index.html"
    if not index_file.exists():
        print("[SETUP] Frontend belum di-build. Membangun aset React Vite...")
        frontend_dir = BASE_DIR / "frontend"
        try:
            subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=True, shell=True)
            print("[SETUP] Build frontend selesai!")
        except Exception as e:
            print(f"[ERROR] Gagal mem-build frontend: {e}")

def open_browser():
    time.sleep(1.5)
    url = "http://localhost:8000"
    print(f"\n=======================================================")
    print(f"🛰️  TACTICAL AI RECONNAISSANCE GCS ONLINE!")
    print(f"🌐  Akses Antarmuka di: {url}")
    print(f"📖  Dokumentasi API di: {url}/docs")
    print(f"=======================================================\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

def main():
    check_frontend_build()
    
    # Buka browser otomatis di thread terpisah
    threading.Thread(target=open_browser, daemon=True).start()
    
    import uvicorn
    # Jalankan FastAPI Uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
