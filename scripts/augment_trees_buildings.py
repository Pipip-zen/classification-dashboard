"""
Script: scripts/augment_trees_buildings.py
Deskripsi:
    Mengunduh subset citra dan label anotasi YOLO untuk objek baru:
      - 9: tree        (Pohon / Vegetasi)
      - 10: building   (Bangunan / Struktur)
    dari Hugging Face repository tanpa terblokir bot-challenge/Cloudflare,
    melakukan re-mapping ID kelas secara otomatis, dan menambahkannya ke:
      data/unified_dataset/train, valid, test
"""

import os
import urllib.request
import json
import random
from pathlib import Path

random.seed(42)

HF_REPO = "Abtinzandi/Obstacle-Detection-Dataset-YOLO"
TREE_ORIG_ID = 12       # Index 12 di Obstacle dataset adalah Tree
BUILDING_ORIG_ID = 1   # Index 1 di Obstacle dataset adalah Building

TARGET_TREE_ID = 9
TARGET_BUILDING_ID = 10

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def download_file(url, out_path):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp, open(out_path, 'wb') as f:
        f.write(resp.read())

def augment():
    base_dir = Path(__file__).resolve().parent.parent
    dataset_dir = base_dir / "data" / "unified_dataset"

    train_img = dataset_dir / "train" / "images"
    train_lbl = dataset_dir / "train" / "labels"
    val_img = dataset_dir / "valid" / "images"
    val_lbl = dataset_dir / "valid" / "labels"
    test_img = dataset_dir / "test" / "images"
    test_lbl = dataset_dir / "test" / "labels"

    for d in [train_img, train_lbl, val_img, val_lbl, test_img, test_lbl]:
        d.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("MENGUNDUH & MENYATUKAN DATASET POHON & BANGUNAN (CLASSES 9 & 10)")
    print("=================================================================")

    # Ambil daftar label files dari test dan train branch
    candidates = []
    for split in ["test", "train"]:
        tree_url = f"https://huggingface.co/api/datasets/{HF_REPO}/tree/main/{split}/labels?limit=300"
        try:
            items = fetch_json(tree_url)
            for it in items:
                candidates.append((split, it["path"]))
        except Exception as e:
            print(f"Warn: gagal mengambil list {split}: {e}")

    print(f"Total kandidat file label ditemukan: {len(candidates)}")

    downloaded_trees = 0
    downloaded_buildings = 0
    max_samples = 90  # 90 sampel berkualitas (pohon & gedung)

    saved_items = []

    for split, lbl_path in candidates:
        if len(saved_items) >= max_samples:
            break

        raw_lbl_url = f"https://huggingface.co/datasets/{HF_REPO}/raw/main/{lbl_path}"
        try:
            req = urllib.request.Request(raw_lbl_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode()
        except Exception:
            continue

        remapped_lines = []
        has_tree = False
        has_building = False

        for line in content.strip().split("\n"):
            parts = line.strip().split()
            if not parts:
                continue
            orig_cls = int(parts[0])
            coords = " ".join(parts[1:])

            if orig_cls == TREE_ORIG_ID:
                remapped_lines.append(f"{TARGET_TREE_ID} {coords}")
                has_tree = True
            elif orig_cls == BUILDING_ORIG_ID:
                remapped_lines.append(f"{TARGET_BUILDING_ID} {coords}")
                has_building = True

        if has_tree or has_building:
            base_name = Path(lbl_path).stem
            img_rel_path = f"{split}/images/{base_name}.jpg"
            raw_img_url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/{img_rel_path}"

            saved_items.append((base_name, raw_img_url, remapped_lines, has_tree, has_building))
            if has_tree:
                downloaded_trees += 1
            if has_building:
                downloaded_buildings += 1
            print(f"[*] Ditemukan ({len(saved_items)}/{max_samples}): {base_name} (Tree={has_tree}, Building={has_building})")

    # Alokasikan ke train (70%), valid (20%), test (10%)
    random.shuffle(saved_items)
    n_total = len(saved_items)
    n_train = int(n_total * 0.75)
    n_val = int(n_total * 0.15)

    train_set = saved_items[:n_train]
    val_set = saved_items[n_train:n_train+n_val]
    test_set = saved_items[n_train+n_val:]

    sets_mapping = [
        ("train", train_set, train_img, train_lbl),
        ("valid", val_set, val_img, val_lbl),
        ("test", test_set, test_img, test_lbl),
    ]

    print("\nMenyimpan citra & label ke folder unified_dataset...")
    for split_name, item_list, out_img_dir, out_lbl_dir in sets_mapping:
        for base_name, img_url, label_lines, _, _ in item_list:
            target_img_path = out_img_dir / f"aerial_{base_name}.jpg"
            target_lbl_path = out_lbl_dir / f"aerial_{base_name}.txt"

            try:
                download_file(img_url, target_img_path)
                with open(target_lbl_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(label_lines) + "\n")
            except Exception as e:
                print(f"Gagal download {base_name}: {e}")

    print(f"\n[SUKSES] Pengayaan dataset selesai:")
    print(f"  • Total gambar baru: {len(saved_items)}")
    print(f"  • Train: {len(train_set)} | Valid: {len(val_set)} | Test: {len(test_set)}")
    print(f"  • Deteksi Pohon: {downloaded_trees} bounding box")
    print(f"  • Deteksi Gedung: {downloaded_buildings} bounding box")

if __name__ == "__main__":
    augment()
