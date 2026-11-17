"""
Script: scripts/download_coral_and_fish.py
Deskripsi:
    Mengunduh dan mengintegrasikan dataset nyata:
    1. Real Coral Reefs (Terumbu Karang Hidup/Mati/Bleached):
       Sumber: sivamani-k/MAFFN_YOLOv5-based-Coral-reefs-health-detection-and-coral-reefs-dataset
       Target: Kelas 6 (coral_reef)
    2. Real Tropical Marine Fish (Ikan Tropis Laut Lepas/Terumbu Karang):
       Sumber: Vinay0905/Fish-Detection-YOLOv8 (Roboflow Universe Fish Dataset)
       Target: Kelas 5 (marine_life)
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).resolve().parent.parent
UNIFIED_DIR = BASE_DIR / "data" / "unified_dataset"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_github_contents(api_url):
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url, out_path):
    if out_path.exists() and out_path.stat().st_size > 0:
        return True
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        with open(out_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def remap_and_save_coral_label(raw_lbl_url, out_lbl_path):
    req = urllib.request.Request(raw_lbl_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            lines = resp.read().decode("utf-8").strip().splitlines()
        remapped_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                # Semua kelas karang dimapping ke kelas 6: coral_reef
                parts[0] = "6"
                remapped_lines.append(" ".join(parts[:5]))
        if remapped_lines:
            with open(out_lbl_path, "w", encoding="utf-8") as f:
                f.write("\n".join(remapped_lines) + "\n")
            return True
    except Exception as e:
        print(f"Error coral label {raw_lbl_url}: {e}")
    return False


def remap_and_save_fish_label(raw_lbl_url, out_lbl_path):
    req = urllib.request.Request(raw_lbl_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            lines = resp.read().decode("utf-8").strip().splitlines()
        remapped_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                # Semua kelas ikan dimapping ke kelas 5: marine_life
                parts[0] = "5"
                remapped_lines.append(" ".join(parts[:5]))
        if remapped_lines:
            with open(out_lbl_path, "w", encoding="utf-8") as f:
                f.write("\n".join(remapped_lines) + "\n")
            return True
    except Exception as e:
        print(f"Error fish label {raw_lbl_url}: {e}")
    return False


def collect_coral_dataset(max_train=300, max_valid=40):
    print("\n[1/2] Mengunduh Dataset Terumbu Karang Nyata (sivamani-k)...")
    base_api = "https://api.github.com/repos/sivamani-k/MAFFN_YOLOv5-based-Coral-reefs-health-detection-and-coral-reefs-dataset/contents"
    
    splits = [("train", max_train), ("valid", max_valid)]
    for split, limit in splits:
        folder_enc = urllib.parse.quote(f"Dataset with annotation in YOLO format/{split}/images")
        api_img = f"{base_api}/{folder_enc}"
        
        try:
            img_items = fetch_github_contents(api_img)
        except Exception as e:
            print(f"  Gagal mengambil daftar gambar coral {split}: {e}")
            continue

        selected = img_items[:limit]
        print(f"  Memproses {len(selected)} citra terumbu karang ({split})...")

        raw_base_ann = f"https://raw.githubusercontent.com/sivamani-k/MAFFN_YOLOv5-based-Coral-reefs-health-detection-and-coral-reefs-dataset/main/Dataset%20with%20annotation%20in%20YOLO%20format/{split}/annotations"

        tgt_img_dir = UNIFIED_DIR / split / "images"
        tgt_lbl_dir = UNIFIED_DIR / split / "labels"
        tgt_img_dir.mkdir(parents=True, exist_ok=True)
        tgt_lbl_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            for item in selected:
                stem = Path(item["name"]).stem
                img_name = f"realcoral_{item['name']}"
                lbl_name = f"realcoral_{stem}.txt"
                
                out_img = tgt_img_dir / img_name
                out_lbl = tgt_lbl_dir / lbl_name
                
                raw_ann_url = f"{raw_base_ann}/{stem}.txt"
                
                tasks.append(executor.submit(download_file, item["download_url"], out_img))
                tasks.append(executor.submit(remap_and_save_coral_label, raw_ann_url, out_lbl))

            for fut in as_completed(tasks):
                fut.result()

        print(f"  [OK] Berhasil mengintegrasikan terumbu karang ({split})!")


def collect_fish_dataset(max_train=300, max_valid=40):
    print("\n[2/2] Mengunduh Dataset Ikan Laut Tropis Nyata (Vinay0905)...")
    base_api = "https://api.github.com/repos/Vinay0905/Fish-Detection-YOLOv8/contents"
    
    splits = [("train", max_train), ("valid", max_valid)]
    for split, limit in splits:
        api_img = f"{base_api}/{split}/images"
        try:
            img_items = fetch_github_contents(api_img)
        except Exception as e:
            print(f"  Gagal mengambil daftar gambar ikan {split}: {e}")
            continue

        selected = img_items[:limit]
        print(f"  Memproses {len(selected)} citra ikan laut tropis ({split})...")

        raw_base_lbl = f"https://raw.githubusercontent.com/Vinay0905/Fish-Detection-YOLOv8/main/{split}/labels"

        tgt_img_dir = UNIFIED_DIR / split / "images"
        tgt_lbl_dir = UNIFIED_DIR / split / "labels"
        tgt_img_dir.mkdir(parents=True, exist_ok=True)
        tgt_lbl_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            for item in selected:
                stem = Path(item["name"]).stem
                img_name = f"tropicalfish_{item['name']}"
                lbl_name = f"tropicalfish_{stem}.txt"
                
                out_img = tgt_img_dir / img_name
                out_lbl = tgt_lbl_dir / lbl_name
                
                raw_lbl_url = f"{raw_base_lbl}/{stem}.txt"
                
                tasks.append(executor.submit(download_file, item["download_url"], out_img))
                tasks.append(executor.submit(remap_and_save_fish_label, raw_lbl_url, out_lbl))

            for fut in as_completed(tasks):
                fut.result()

        print(f"  [OK] Berhasil mengintegrasikan ikan laut tropis ({split})!")


if __name__ == "__main__":
    collect_coral_dataset(max_train=250, max_valid=35)
    collect_fish_dataset(max_train=250, max_valid=35)
    print("\n[SELESAI] Penambahan dataset nyata terumbu karang dan ikan laut selesai.")
