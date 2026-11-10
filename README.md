# 🛡️ Tactical AI Surveillance & Reconnaissance Dashboard
**Mata Kuliah:** Workshop Kecerdasan Buatan (Bab 5 - Image Classification & Object Detection)  
**Kelompok:** Kelompok 1  
**Tech Stack:** Python 3.10+, Streamlit, Ultralytics YOLOv8 (Transfer Learning), OpenCV, MSS  

---

## 📑 Dokumentasi Resmi (Spec-Driven Development)
- **PRD Resmi:** [`docs/PRD-TACTICAL-SURVEILLANCE-AI.md`](docs/PRD-TACTICAL-SURVEILLANCE-AI.md)
- **Kebutuhan Sistem (SRS):** [`docs/specs/01-system-requirements.md`](docs/specs/01-system-requirements.md)
- **Taksonomi & Dataset Spec:** [`docs/specs/02-ai-and-dataset-spec.md`](docs/specs/02-ai-and-dataset-spec.md)
- **CV Pipeline Spec:** [`docs/specs/03-cv-pipeline-spec.md`](docs/specs/03-cv-pipeline-spec.md)
- **Arsitektur Perangkat Lunak:** [`docs/specs/04-software-architecture.md`](docs/specs/04-software-architecture.md)
- **Protokol Uji Mingguan (Virtual Testbench):** [`docs/specs/05-weekly-verification-and-testbench.md`](docs/specs/05-weekly-verification-and-testbench.md)

---

## 🎯 Taksonomi Terpadu 9 Kelas (Air & Darat)
| ID | Nama Kelas | Domain Lingkungan | Status Ancaman (*Threat Status*) | Referensi Lebar ($W_{real}$) |
|:---:|---|:---:|:---:|:---:|
| `0` | `soldier` | Land | **HAZARD (Merah)** *(Dievaluasi Tim A vs Tim B via Stage 2)* | $0.5\text{ m}$ |
| `1` | `military_vehicle` | Land | **HAZARD (Merah)** *(Tank, IFV, Armored Car)* | $3.2\text{ m}$ |
| `2` | `civilian` | Land | **NEUTRAL (Hijau)** *(Manusia & Kendaraan Sipil)* | $0.5\text{ m}$ |
| `3` | `ship` | Surface Water | **HAZARD / WARNING (Oranye)** *(Kapal Permukaan Air)* | $25.0\text{ m}$ |
| `4` | `submarine` | Underwater | **HAZARD (Merah)** *(Kapal Selam Militer)* | $12.0\text{ m}$ |
| `5` | `marine_life` | Underwater | **NEUTRAL (Hijau)** *(Ikan & Biota Bawah Air)* | $0.4\text{ m}$ |
| `6` | `coral_reef` | Underwater | **NEUTRAL (Hijau)** *(Terumbu Karang / Formasi Alami)* | $1.5\text{ m}$ |
| `7` | `rov` | Underwater | **NEUTRAL (Cyan)** *(Wahana Friendly ROV)* | $0.8\text{ m}$ |
| `8` | `fpv_drone` | Land / Air | **WARNING (Oranye)** *(Drone FPV Udara)* | $0.4\text{ m}$ |

---

## 🚀 Panduan Menjalankan Sistem

### 1. Instalasi Dependensi
```bash
pip install -r requirements.txt
```

### 2. Status Dataset Terpadu (`data/unified_dataset/`)
Dataset terpadu telah otomatis diseimbangkan dan disusun:
- **Train Set:** 2.660 citra
- **Valid Set:** 352 citra
- **Test Set:** 243 citra

### 3. Melatih Model (Training YOLOv8 Transfer Learning)
Jalankan perintah berikut di terminal:
```bash
python scripts/train_yolo.py
```
*Bobot model terbaik akan otomatis tersimpan di folder `models/best.pt`.*

### 4. Menjalankan Dashboard Streamlit
```bash
streamlit run app.py
```

Dashboard akan otomatis terbuka di browser pada URL: `http://localhost:8501`.

---

## 🧭 Halaman Dashboard
1. **Beranda (`app.py`):** Status operasional sistem, statistik model, dan matriks ancaman.
2. **`1_Live_Surveillance.py`:** Screen mirroring window aplikasi ROV/Drone, simulasi video testbench mingguan, dan telemetri ancaman real-time.
3. **`2_Media_Analysis.py`:** Upload video rekaman MP4 & foto tunggal, estimasi jarak kamera, dan ekspor tabel log misi ke CSV.
4. **`3_Image_Stitching.py`:** Penggabungan foto jalur patroli menjadi citra panorama mulus.
5. **`4_Image_Inpainting.py`:** Sanitasi dan penyensoran koordinat GPS OSD dan noise kamera.
6. **`5_Dataset_Helper.py`:** Pemeriksaan visual sampel data dan kontrol parameter training.
