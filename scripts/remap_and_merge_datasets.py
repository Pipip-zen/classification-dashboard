"""
Script: scripts/remap_and_merge_datasets.py
Deskripsi:
    Menggabungkan 6 dataset Roboflow (ds1 s/d ds6) ke dalam data/unified_dataset/
    secara CEPAT dengan penyeimbangan sampel (subsampling) dan pemetaan ulang label:
      0: soldier            (Prajurit Darat - Tim A / Tim B)
      1: military_vehicle   (Kendaraan Tempur Darat: Tank, IFV, Armored Car)
      2: civilian           (Sipil: Manusia & Kendaraan Sipil)
      3: ship               (Kapal Permukaan Air: Militer / Nelayan)
      4: submarine          (Kapal Selam Bawah Air)
      5: marine_life        (Biota Laut: Ikan, Kepiting, dll)
      6: coral_reef         (Terumbu Karang & Tanaman Bawah Air)
      7: rov                (ROV Drone Bawah Air)
      8: fpv_drone          (Drone Udara FPV)
"""

import os
import shutil
import random
import yaml
from pathlib import Path
from collections import defaultdict

random.seed(42)

UNIFIED_CLASSES = {
    0: "soldier",
    1: "military_vehicle",
    2: "civilian",
    3: "ship",
    4: "submarine",
    5: "marine_life",
    6: "coral_reef",
    7: "rov",
    8: "fpv_drone",
}

# Target kuota gambar per kelas per split agar seimbang dan training cepat
SAMPLE_LIMITS = {
    "train": 350,
    "valid": 50,
    "test": 30
}

DATASET_CLASS_MAPPING = {
    "ds1": {
        "aquatic animal": 5,
        "human activity": 2,
    },
    "ds2": {
        "animal_fish": 5,
        "animal_crab": 5,
        "animal_eel": 5,
        "animal_starfish": 5,
        "animal_shells": 5,
        "animal_etc": 5,
        "plant": 6,
        "rov": 7,
    },
    "ds3": {
        "soldier": 0,
        "tank": 1,
        "ifv": 1,
        "armored car": 1,
        "military truck": 1,
        "fighter jet": 1,
        "helicopter": 1,
        "civilian": 2,
        "fpv": 8,
    },
    "ds4": {
        "ship": 3,
    },
    "ds5": {
        "bus": 2,
        "mobil": 2,
        "mobil van": 2,
        "truck": 2,
    },
    "ds6": {
        "submarine": 4,
    }
}


def load_dataset_names(ds_folder: Path) -> dict:
    yaml_path = ds_folder / "data.yaml"
    if not yaml_path.exists():
        return {}
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        names = data.get("names", [])
        if isinstance(names, list):
            return {i: str(n).lower().strip() for i, n in enumerate(names)}
        elif isinstance(names, dict):
            return {int(k): str(v).lower().strip() for k, v in names.items()}
    return {}


def merge_and_balance():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    unified_dir = data_dir / "unified_dataset"

    # Reset direktori tujuan
    if unified_dir.exists():
        shutil.rmtree(unified_dir)
    unified_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================", flush=True)
    print("PROSES PENYATUAN & PENYEIMBANGAN CEPAT DATASET ROBOFLOW", flush=True)
    print("=================================================================", flush=True)

    # candidates[split][class_id] = list of (ds_name, img_path, remapped_lines)
    candidates = {
        "train": defaultdict(list),
        "valid": defaultdict(list),
        "test": defaultdict(list)
    }

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    for ds_name, mapping_rules in DATASET_CLASS_MAPPING.items():
        ds_path = data_dir / ds_name
        if not ds_path.exists():
            continue

        raw_names = load_dataset_names(ds_path)
        print(f"[*] Scanning {ds_name}...", end="", flush=True)
        ds_collected = 0

        for split in ["train", "valid", "test"]:
            img_dir = ds_path / split / "images"
            lbl_dir = ds_path / split / "labels"

            if not img_dir.exists() or not lbl_dir.exists():
                continue

            target_quota = SAMPLE_LIMITS[split] + 100

            # Gunakan os.scandir untuk kecepatan maksimum di Windows
            with os.scandir(img_dir) as entries:
                for entry in entries:
                    if not entry.is_file():
                        continue
                    suffix = os.path.splitext(entry.name)[1].lower()
                    if suffix not in valid_exts:
                        continue

                    stem = os.path.splitext(entry.name)[0]
                    lbl_path = lbl_dir / f"{stem}.txt"
                    if not lbl_path.exists():
                        continue

                    remapped_lines = []
                    primary_class = None

                    try:
                        with open(lbl_path, "r", encoding="utf-8") as lf:
                            for line in lf:
                                parts = line.strip().split()
                                if not parts:
                                    continue
                                old_cls = int(parts[0])
                                orig_name = raw_names.get(old_cls, "")
                                if orig_name in mapping_rules:
                                    new_cls = mapping_rules[orig_name]
                                    parts[0] = str(new_cls)
                                    remapped_lines.append(" ".join(parts))
                                    if primary_class is None:
                                        primary_class = new_cls
                    except Exception:
                        continue

                    if remapped_lines and primary_class is not None:
                        # Jika kelas ini sudah cukup banyak untuk split ini, lewati untuk menghemat waktu
                        if len(candidates[split][primary_class]) < target_quota:
                            candidates[split][primary_class].append(
                                (ds_name, Path(entry.path), remapped_lines)
                            )
                            ds_collected += 1

        print(f" Selesai! (Dipilih {ds_collected} gambar representatif)", flush=True)

    print("\n[*] Menyalin dan menyusun dataset terpadu...", flush=True)

    final_stats = {
        "train": defaultdict(int),
        "valid": defaultdict(int),
        "test": defaultdict(int)
    }

    for split in ["train", "valid", "test"]:
        tgt_img_dir = unified_dir / split / "images"
        tgt_lbl_dir = unified_dir / split / "labels"
        tgt_img_dir.mkdir(parents=True, exist_ok=True)
        tgt_lbl_dir.mkdir(parents=True, exist_ok=True)

        limit = SAMPLE_LIMITS[split]

        for cls_id, items in candidates[split].items():
            random.shuffle(items)
            selected = items[:limit]

            for ds_name, img_path, lines in selected:
                unique_name = f"{ds_name}_{img_path.stem}"
                tgt_img_file = tgt_img_dir / f"{unique_name}{img_path.suffix}"
                tgt_lbl_file = tgt_lbl_dir / f"{unique_name}.txt"

                shutil.copy2(img_path, tgt_img_file)
                with open(tgt_lbl_file, "w", encoding="utf-8") as out_lbl:
                    out_lbl.write("\n".join(lines) + "\n")

                final_stats[split][cls_id] += 1

    # Tulis data.yaml
    yaml_data = {
        "path": str(unified_dir.resolve().as_posix()),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(UNIFIED_CLASSES),
        "names": UNIFIED_CLASSES
    }

    with open(unified_dir / "data.yaml", "w", encoding="utf-8") as yf:
        yaml.dump(yaml_data, yf, sort_keys=False)

    print("\n=================================================================", flush=True)
    print("HASIL DATASET TERPADU (data/unified_dataset/):", flush=True)
    print("=================================================================", flush=True)
    for cls_id, name in UNIFIED_CLASSES.items():
        tr = final_stats["train"][cls_id]
        va = final_stats["valid"][cls_id]
        te = final_stats["test"][cls_id]
        print(f" [{cls_id}] {name:<18}: Train={tr:>4} | Valid={va:>3} | Test={te:>3}", flush=True)

    total_train = sum(final_stats["train"].values())
    total_valid = sum(final_stats["valid"].values())
    total_test = sum(final_stats["test"].values())
    print("-----------------------------------------------------------------", flush=True)
    print(f" TOTAL SEMUA CITRA TERPADU : Train={total_train} | Valid={total_valid} | Test={total_test}", flush=True)
    print(f" Konfigurasi data.yaml     : {unified_dir / 'data.yaml'}", flush=True)
    print("=================================================================\n", flush=True)


if __name__ == "__main__":
    merge_and_balance()
