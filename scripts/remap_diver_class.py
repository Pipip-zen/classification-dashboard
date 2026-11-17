"""
Script: scripts/remap_diver_class.py
Deskripsi:
    Memetakan ulang label 'human activity' di dataset underwater (ds1_*)
    dari Class 2 (civilian) menjadi Class 11 (diver / Penyelam Bawah Air)
    pada seluruh split (train, valid, test).
"""

from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data" / "unified_dataset"

total_remapped_boxes = 0
total_files_modified = 0

for split in ["train", "valid", "test"]:
    lbl_dir = data_dir / split / "labels"
    if not lbl_dir.exists():
        continue

    files = list(lbl_dir.glob("ds1_*.txt"))
    print(f"[*] Memproses {len(files)} file ds1 pada split '{split}'...")

    for f_path in files:
        with open(f_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        file_changed = False

        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue

            cls_id = int(parts[0])
            coords = " ".join(parts[1:])

            if cls_id == 2:  # Civilian di ds1 adalah diver/penyelam
                new_lines.append(f"11 {coords}\n")
                total_remapped_boxes += 1
                file_changed = True
            else:
                new_lines.append(line)

        if file_changed:
            with open(f_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            total_files_modified += 1

print("\n==========================================================")
print("[SUKSES] Pemetaan ulang kelas 'diver' (11) selesai:")
print(f"  • Berkas label diperbarui : {total_files_modified} berkas")
print(f"  • Anotasi Penyelam (Diver): {total_remapped_boxes} bounding box dipetakan ke Class 11")
print("==========================================================")
