"""
Script: scripts/remap_to_8_classes.py
Deskripsi:
    1. Menghapus 4 kelas dari dataset:
       - ship (lama: 3)
       - rov (lama: 7)
       - fpv_drone (lama: 8)
       - building (lama: 10)
    2. Menyusun ulang indeks 8 kelas tersisa berdasarkan domain kokpit:
       - Domain Drone: 0: soldier, 1: military_vehicle, 2: civilian, 3: tree
       - Domain ROV:   4: submarine, 5: marine_life, 6: coral_reef, 7: diver
    3. Menghapus berkas gambar & label yang menjadi kosong (tidak memiliki target aktif).
    4. Memperbarui data/unified_dataset/data.yaml dan menghapus berkas *.cache lama.
"""

from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "unified_dataset"

OLD_TO_NEW_MAP = {
    0: 0,   # soldier
    1: 1,   # military_vehicle
    2: 2,   # civilian
    9: 3,   # tree (pindah ke indeks 3, grup Drone)
    4: 4,   # submarine
    5: 5,   # marine_life
    6: 6,   # coral_reef
    11: 7   # diver (pindah ke indeks 7, grup ROV)
}

REMOVED_CLASSES = {3, 7, 8, 10}

NAMES_8 = {
    0: "soldier",
    1: "military_vehicle",
    2: "civilian",
    3: "tree",
    4: "submarine",
    5: "marine_life",
    6: "coral_reef",
    7: "diver"
}


def remap_split(split_name: str):
    lbl_dir = DATA_DIR / split_name / "labels"
    img_dir = DATA_DIR / split_name / "images"

    if not lbl_dir.exists() or not img_dir.exists():
        print(f"[-] Split {split_name} tidak ditemukan, lewati.")
        return

    print(f"\n[*] Memproses split '{split_name}'...")
    total_labels = 0
    retained_files = 0
    deleted_empty_files = 0
    class_counter = Counter()

    # Hapus file cache YOLO lama agar cache di-generate ulang
    cache_file = DATA_DIR / split_name / "labels.cache"
    if cache_file.exists():
        cache_file.unlink(missing_ok=True)
        print(f"  [x] Cache lama dihapus: {cache_file.name}")

    lbl_files = list(lbl_dir.glob("*.txt"))
    total_labels = len(lbl_files)

    for lbl_path in lbl_files:
        lines = lbl_path.read_text(encoding="utf-8").splitlines()
        new_lines = []

        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
            old_cls = int(parts[0])
            if old_cls in OLD_TO_NEW_MAP:
                new_cls = OLD_TO_NEW_MAP[old_cls]
                parts[0] = str(new_cls)
                new_lines.append(" ".join(parts))
                class_counter[new_cls] += 1

        stem = lbl_path.stem
        # Cari file gambar yang cocok (bisa .jpg, .png, .jpeg, .webp)
        matching_imgs = list(img_dir.glob(f"{stem}.*"))

        if not new_lines:
            # Tidak ada target yang tersisa -> Hapus label dan gambar
            lbl_path.unlink(missing_ok=True)
            for img_p in matching_imgs:
                img_p.unlink(missing_ok=True)
            deleted_empty_files += 1
        else:
            # Tulis label baru
            lbl_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            retained_files += 1

    print(f"  [OK] Hasil '{split_name}':")
    print(f"       Total awal  : {total_labels} file")
    print(f"       Dipertahankan: {retained_files} file dengan target aktif")
    print(f"       Dihapus      : {deleted_empty_files} file kosong")
    print(f"       Distribusi 8 Kelas: {dict(sorted(class_counter.items()))}")


def update_data_yaml():
    yaml_path = DATA_DIR / "data.yaml"
    content = f"""path: {DATA_DIR.as_posix()}
train: train/images
val: valid/images
test: test/images
nc: 8
names:
  0: soldier
  1: military_vehicle
  2: civilian
  3: tree
  4: submarine
  5: marine_life
  6: coral_reef
  7: diver
"""
    yaml_path.write_text(content, encoding="utf-8")
    print(f"\n[OK] Berhasil memperbarui {yaml_path} menjadi 8 kelas terpadu.")


def main():
    print("==========================================================")
    print("REMAP DATASET TAKTIS GCS MENJADI 8 KELAS TERPADU")
    print("Kelas Dihapus: ship (3), rov (7), fpv_drone (8), building (10)")
    print("Kelas Baru   : 4 Drone (0-3) + 4 ROV (4-7)")
    print("==========================================================")

    for split in ["train", "valid", "test"]:
        remap_split(split)

    update_data_yaml()
    print("\n[SELESAI] Dataset siap untuk retraining YOLOv8 8 kelas.")


if __name__ == "__main__":
    main()
