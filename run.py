"""
Launcher Tunggal: Tactical AI Ground Control Station (GCS)
Menjalankan server FastAPI pada port 8000 yang menyajikan API & Web Frontend React secara terpadu.
Otomatis mendeteksi dan menggunakan Virtual Environment (.venv).
"""

import sys
import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Auto-detect Virtual Environment (.venv) jika user menjalankan lewat global Python
venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if venv_python.exists():
    try:
        current_exe = Path(sys.executable).resolve()
        target_exe = venv_python.resolve()
        if current_exe != target_exe:
            print(f"[AUTO-ENV] Mendeteksi Python Global ({current_exe.name}).")
            print(f"[AUTO-ENV] Otomatis beralih ke Virtual Environment: {venv_python} ...\n")
            result = subprocess.run([str(venv_python)] + sys.argv)
            sys.exit(result.returncode)
    except Exception as e:
        print(f"[WARN] Gagal auto-switch ke .venv: {e}")

import webbrowser
import threading
import time

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
    
    try:
        import uvicorn
    except ImportError:
        print("[ERROR] Pustaka 'uvicorn' belum terpasang.")
        print("Silakan jalankan: pip install -r requirements.txt")
        sys.exit(1)

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
