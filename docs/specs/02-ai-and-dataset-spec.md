# SPEC-02: AI TAXONOMY & DATASET INTEGRATION SPECIFICATION
**Proyek:** Tactical Surveillance Dashboard AI (Air & Darat)  
**Model Framework:** Ultralytics YOLOv8 / YOLO11 (PyTorch)  

---

## 1. Taksonomi Kelas & Pemetaan Status Ancaman

Seluruh dataset publik yang diunduh dari Roboflow akan distandardisasi ke dalam skema kelas terpadu berikut:

| ID | Nama Kelas (*Unified Class*) | Domain Lingkungan | Status Ancaman (*Threat Status*) | Dimensi Referensi ($W_{real}$) |
|:---:|---|---|:---:|:---:|
| `0` | `soldier_team_a` | Land | **Berbahaya / Hazard** (Merah) | $0.5\text{ m}$ (lebar pundak) |
| `1` | `soldier_team_b` | Land | **Berbahaya / Hazard** (Merah) | $0.5\text{ m}$ (lebar pundak) |
| `2` | `civilian` | Land / Water | **Netral / Aman** (Hijau) | $0.5\text{ m}$ |
| `3` | `warship` | Surface Water | **Berbahaya / Hazard** (Merah) | $15.0\text{ m} - 50.0\text{ m}$ |
| `4` | `fishing_boat` | Surface Water | **Netral / Aman** (Hijau) | $4.0\text{ m} - 10.0\text{ m}$ |
| `5` | `submarine` | Underwater / Surface | **Berbahaya / Hazard** (Merah) | $8.0\text{ m} - 25.0\text{ m}$ |
| `6` | `naval_mine` | Underwater | **Berbahaya / Hazard** (Merah) | $0.8\text{ m} - 1.2\text{ m}$ |
| `7` | `marine_life` (ikan/biota) | Underwater | **Netral / Aman** (Hijau) | $0.3\text{ m}$ |
| `8` | `coral_reef` | Underwater | **Netral / Aman** (Hijau) | $1.5\text{ m}$ |

---

## 2. Cara Mengaplikasikan Dataset dari Roboflow

### 2.1. Format Ekspor Roboflow yang Wajib Dipilih
Saat mengunduh (*export*) dataset dari Roboflow, pilih format:
> **Format:** `YOLOv8 PyTorch TXT` (Format ini kompatibel langsung dengan YOLOv8 dan YOLO11).

Struktur folder hasil unduhan Roboflow biasanya berbentuk:
```text
dataset_roboflow_downloaded/
├── train/
│   ├── images/
│   └── labels/
├── valid/
│   ├── images/
│   └── labels/
├── test/
│   ├── images/
│   └── labels/
└── data.yaml
```

### 2.2. Menyatukan Beberapa Dataset Roboflow (Dataset Merger & Class Remapping)
Karena Anda mengambil beberapa dataset (misal: 1 dataset tentara/darat + 1 dataset underwater + 1 dataset kapal), dataset-dataset ini memiliki indeks kelas yang saling tumpang tindih.

Kita akan menyediakan script otomasi: `scripts/remap_and_merge_datasets.py` yang bertugas:
1. Membaca file `.txt` label dari masing-masing dataset Roboflow.
2. Memetakan label lama $\to$ label terpadu sesuai tabel taksonomi di atas.
3. Menggabungkan file gambar dan label ke dalam direktori kerja:
   ```text
   data/
   ├── unified_dataset/
   │   ├── train/ (images, labels)
   │   ├── val/   (images, labels)
   │   └── test/  (images, labels)
   └── data.yaml
   ```

### 2.3. Struktur File Konfigurasi `data.yaml`
```yaml
path: d:/Pelajaran/Kuliah/SMT 5/Workshop Kecerdasan Buatan/Projek/data/unified_dataset
train: train/images
val: valid/images
test: test/images

names:
  0: soldier_team_a
  1: soldier_team_b
  2: civilian
  3: warship
  4: fishing_boat
  5: submarine
  6: naval_mine
  7: marine_life
  8: coral_reef
```

---

## 3. Strategi Pelatihan (Transfer Learning Pipeline)

1. **Base Model Pre-trained:** `yolov8n.pt` / `yolo11n.pt` (Nano untuk inferensi super cepat di laptop/dashboard) atau `yolov8s.pt` / `yolo11s.pt` (Small untuk akurasi lebih tinggi).
2. **Hyperparameters Standar:**
   - Image size: `640x640`
   - Epochs: `50 - 100` (dengan *Early Stopping* patience 10)
   - Batch size: `16` (bila menggunakan GPU CUDA) atau `8` (CPU)
   - Optimizer: `auto` (AdamW / SGD)
3. **Metrik Keberhasilan:**
   - $mAP_{50} \ge 0.75$
   - $mAP_{50-95} \ge 0.50$
   - Inference time $\le 30\text{ ms}$ pada GPU atau $\le 100\text{ ms}$ pada CPU.

