"""
Script: scripts/append_buildings_and_trees.py
Deskripsi:
    Memperkaya dataset data/unified_dataset dengan anotasi objek baru:
      - Class 9: tree        (Pohon / Vegetasi)
      - Class 10: building   (Bangunan / Struktur)
    menggunakan model Teacher OpenImages (yolov8n-oiv7) pada split train/valid/test.
"""

from pathlib import Path
from ultralytics import YOLO

model = YOLO("yolov8n-oiv7.pt")

tree_classes = {553, 364}               # Tree, Palm tree
building_classes = {70, 257, 354}       # Building, House, Office building

CONF_THRESHOLD = 0.42

base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data" / "unified_dataset"

total_added_trees = 0
total_added_bldgs = 0
total_modified_files = 0

for split in ["train", "valid", "test"]:
    img_dir = data_dir / split / "images"
    lbl_dir = data_dir / split / "labels"
    if not img_dir.exists() or not lbl_dir.exists():
        continue

    # Fokuskan pemindaian pada citra skenario darat & udara (ds3, ds4, ds5, aerial)
    images = [
        p for p in img_dir.glob("*.jpg")
        if p.name.startswith("ds3_") or p.name.startswith("ds4_") or p.name.startswith("ds5_") or p.name.startswith("aerial_")
    ]
    print(f"[*] Memindai {len(images)} gambar darat/aerial pada split '{split}'...")

    for img_p in images:
        lbl_p = lbl_dir / f"{img_p.stem}.txt"
        
        # Baca label yang sudah ada agar tidak duplikat
        existing_lines = []
        if lbl_p.exists():
            with open(lbl_p, "r", encoding="utf-8") as f:
                existing_lines = [l.strip() for l in f if l.strip()]

        res = model.predict(str(img_p), conf=CONF_THRESHOLD, verbose=False)
        new_lines = []

        for box in res[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            xywh = box.xywhn[0].cpu().numpy()
            x, y, w, h = xywh

            if c in tree_classes:
                new_line = f"9 {x:.6f} {y:.6f} {w:.6f} {h:.6f}"
                new_lines.append(new_line)
                total_added_trees += 1
            elif c in building_classes:
                new_line = f"10 {x:.6f} {y:.6f} {w:.6f} {h:.6f}"
                new_lines.append(new_line)
                total_added_bldgs += 1

        if new_lines:
            all_lines = existing_lines + new_lines
            with open(lbl_p, "w", encoding="utf-8") as f:
                f.write("\n".join(all_lines) + "\n")
            total_modified_files += 1

print("\n==========================================================")
print("[SUKSES] Pengayaan taksonomi 11 kelas selesai:")
print(f"  • Berkas label diperbarui : {total_modified_files} berkas")
print(f"  • Anotasi Pohon (Tree)    : +{total_added_trees} bounding box")
print(f"  • Anotasi Bangunan (Bldg) : +{total_added_bldgs} bounding box")
print("==========================================================")
