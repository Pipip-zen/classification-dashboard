# VANGUARD AI — Tactical Ground Control Station
**Visual AI for Neutralization & Ground-Aquatic Reconnaissance Drone (ROV Danau & Drone Spectator)**

* **Mata Kuliah:** Workshop Kecerdasan Buatan (Image Classification & Object Detection)
* **Kelompok:** Kelompok 1
* **Nama Sistem:** **VANGUARD AI** (*Visual AI for Neutralization & Ground-Aquatic Reconnaissance Drone*)
* **Arsitektur:** Decoupled High-Performance Python Backend (FastAPI) + Modern Web Workstation (React, TypeScript, Tailwind CSS)
* **Single-Port Serving:** Port 8000 (`http://localhost:8000`)
* **AI Core:** PyTorch CUDA, Ultralytics YOLOv8n (`models/best.pt`), OpenCV

---

## 1. Panduan Menjalankan Sistem

### A. Persyaratan Sistem
* Python 3.10 atau 3.11 (Virtual Environment `.venv` direkomendasikan)
* Node.js v18+ & npm (hanya jika ingin memodifikasi source frontend)
* GPU NVIDIA dengan CUDA (opsional, CPU didukung otomatis)

### B. Menjalankan Ground Control Station (GCS)
Cukup jalankan satu perintah dari root folder projek:

```bash
python run.py
```

*(Atau di Windows, klik dua kali berkas `run_gcs.bat`)*

Skrip `run.py` otomatis mendeteksi virtual environment `.venv`, menyalakan server FastAPI, dan membuka browser pada:
* **Antarmuka GCS:** `http://localhost:8000`
* **Dokumentasi API Swagger:** `http://localhost:8000/docs`

---

## 2. Struktur Arsitektur Sistem

```
projek/
├── core/                           # Python AI & Computer Vision Core
│   ├── detector.py                 # TacticalDetector (YOLOv8 + Foliage Guard)
│   ├── threat_evaluator.py         # ThreatEvaluator (ROV vs Drone Logic)
│   ├── distance_estimator.py       # DistanceEstimator (Pinhole Camera Model)
│   ├── stream_capture.py           # Multi-Source Stream Handler
│   ├── stitcher.py                 # Panorama Stitching Pipeline
│   └── inpainter.py                # Telea & Navier-Stokes Inpainter
├── server/                         # FastAPI Backend (REST & WebSocket)
│   ├── main.py                     # Entry point FastAPI & Static SPA Hosting
│   ├── state.py                    # Thread-safe global state & WS broadcaster
│   ├── routes/                     # Router API: stream, analysis, stitching, inpainting, dataset, system
│   └── services/                   # stream_worker.py (background video loop)
├── frontend/                       # Modern React TypeScript Frontend (Workstation UI)
│   ├── src/
│   │   ├── components/layout/      # TopNavbar (Brand & Cockpit Switcher)
│   │   ├── pages/                  # LiveCockpit, MediaAnalysis, StitchingView, InpaintingView, DatasetView
│   │   └── types.ts                # Strict TypeScript Interfaces
│   ├── dist/                       # Production Static Build
│   └── package.json                # React, Vite, Tailwind CSS, Lucide Icons
├── models/best.pt                  # Bobot model YOLOv8n terverifikasi
├── testbench_samples/              # Sampel video (Hutan, Kota, Danau) & citra uji
├── run.py                          # Launcher tunggal self-healing (.venv auto-detect)
├── run_gcs.bat                     # Windows Batch Launcher
└── requirements.txt                # Dependensi Python
```

---

## 3. Taksonomi Terpadu 12 Kelas (ROV & Drone)

| ID | Nama Kelas | Domain | Status Ancaman | Referensi Lebar ($W_{real}$) | Mode Cockpit |
|:---:|---|:---:|:---:|:---:|:---:|
| `0` | `soldier` | Land | **HAZARD (Merah)** | 0.5 m | Drone |
| `1` | `military_vehicle` | Land | **NEUTRAL (Kuning/Oranye)** | 3.2 m | Drone |
| `2` | `civilian` | Land | **NEUTRAL (Hijau)** | 0.5 m | Drone |
| `3` | `ship` | Water | **HAZARD (Merah)** | 25.0 m | ROV |
| `4` | `submarine` | Water | **HAZARD (Merah)** | 12.0 m | ROV |
| `5` | `marine_life` | Water | **NEUTRAL (Hijau)** | 0.4 m | ROV |
| `6` | `coral_reef` | Water | **NEUTRAL (Hijau)** | 1.5 m | ROV |
| `7` | `rov` | Water | **NEUTRAL (Cyan)** | 0.8 m | ROV |
| `8` | `fpv_drone` | Land/Air | **NEUTRAL (Hijau)** | 0.4 m | Drone |
| `9` | `tree` | Land | **NEUTRAL (Hijau Hutan)** | 3.0 m | Drone |
| `10` | `building` | Land | **NEUTRAL (Abu-abu)** | 10.0 m | Drone |
| `11` | `diver` | Water | **NEUTRAL (Biru Langit)** | 0.6 m | ROV |

---

## 4. Modul Antarmuka GCS

1. **Live Cockpit:**
   * Tata letak split-screen workstation (70% area video bersih, 30% panel kontrol terstruktur).
   * Mode ganda instan: ROV Danau vs Drone Spectator.
   * Multi-sumber: Virtual Testbench MP4 (Hutan & Pejalan Kaki, Perkotaan, Bawah Air), YouTube Live URL, Screen Mirroring, RTSP/UDP/SDP, USB Webcam, dan TikTok Live.
   * OSD cerdas: Reticle crosshair, Dusk/Low-Light aerial enhancer, Confidence gate slider, dan target manifest dengan estimasi jarak meter.
2. **Media Analysis:**
   * Inspeksi foto offline mendalam dengan bounding box taktis, rincian confidence score, status sektor ancaman, dan tombol ekspor CSV.
3. **Panorama Stitching:**
   * Penggabungan multi-citra patroli beririsan (overlap &gt; 30%) menjadi bidang pandang lebar dengan pemangkasan batas hitam otomatis.
4. **Image Inpainting:**
   * Kanvas interaktif HTML5 dengan kuas mouse untuk menandai objek yang ingin dihapus atau disensor (algoritma Telea & Navier-Stokes).
5. **Dataset Explorer:**
   * Ringkasan 12 kelas sensorik dan status integritas data training.

---

## 5. Protokol Pengujian & Verifikasi

Uji sistem otomatis dapat dijalankan melalui terminal:

```bash
# 1. Uji End-to-End API FastAPI, MJPEG Stream, dan Single-Port Static Serving:
python scripts/test_gcs_api.py

# 2. Uji Integritas 7 Modul Inti (Computer Vision Core & Estimasi Jarak):
python scripts/verify_all_modules.py
```
