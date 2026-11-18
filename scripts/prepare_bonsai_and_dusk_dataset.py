"""
Script: scripts/prepare_bonsai_and_dusk_dataset.py
Deskripsi:
    1. Mengunduh dan menyiapkan dataset citra Pohon Bonsai, Tanaman Pangkas (Topiary),
       dan Tanaman Hias Taman dari Wikimedia Commons.
    2. Menempatkan dan mengaugmentasikan bonsai pada latar pekarangan/trotoar aerial
       dengan label '9: tree'.
    3. Menerapkan augmentasi Senja / Sore Hari (Dusk / Twilight Simulation):
       - Pengurangan intensitas cahaya (40-60%)
       - Pergeseran temperatur warna ke nuansa senja/kebiruan
       - Peningkatan kontras siluet pejalan kaki (civilian) dan tanaman
    4. Menambahkan sampel ke data/unified_dataset/train dan valid untuk retraining model.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
UNIFIED_DIR = BASE_DIR / "data" / "unified_dataset"
TRAIN_IMG_DIR = UNIFIED_DIR / "train" / "images"
TRAIN_LBL_DIR = UNIFIED_DIR / "train" / "labels"
VALID_IMG_DIR = UNIFIED_DIR / "valid" / "images"
VALID_LBL_DIR = UNIFIED_DIR / "valid" / "labels"

RAW_BONSAI_DIR = BASE_DIR / "data" / "raw_bonsai"
RAW_BONSAI_DIR.mkdir(parents=True, exist_ok=True)


def download_bonsai_images():
    print("=================================================================")
    print("[1/3] MENGUNDUH DATASET BONSAI & POHON PANGKAS DARI REPOSITORI")
    print("=================================================================")

    search_queries = [
        "bonsai tree",
        "bonsai",
        "japanese bonsai",
        "penjing",
        "topiary garden",
        "pruned shrub",
        "boxwood topiary",
        "ficus bonsai"
    ]

    downloaded = 0
    seen_urls = set()

    for q in search_queries:
        encoded_q = urllib.parse.quote(q)
        api_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={encoded_q}&gsrlimit=12&prop=pageimages&pithumbsize=800"
        req = urllib.request.Request(api_url, headers={"User-Agent": "TacticalAISurveillance/2.0 (student research)"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                pages = data.get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    thumb = pdata.get("thumbnail", {}).get("source")
                    title = pdata.get("title", f"img_{pid}").replace(" ", "_").replace("/", "_")
                    if thumb and thumb not in seen_urls:
                        seen_urls.add(thumb)
                        out_file = RAW_BONSAI_DIR / f"bonsai_{downloaded:03d}_{title[:25]}.jpg"
                        if not out_file.exists():
                            try:
                                img_req = urllib.request.Request(thumb, headers={"User-Agent": "TacticalAISurveillance/2.0 (student research)"})
                                with urllib.request.urlopen(img_req, timeout=8) as img_resp, open(out_file, "wb") as f_out:
                                    f_out.write(img_resp.read())
                                downloaded += 1
                                print(f"  [+] Terunduh: {out_file.name}")
                            except Exception as e:
                                pass
        except Exception as e:
            print(f"  [-] Query '{q}' lewati: {e}")

    print(f"[*] Total {len(list(RAW_BONSAI_DIR.glob('*.jpg')))} citra bonsai tersimpan di {RAW_BONSAI_DIR}.")


def create_dusk_augmented_samples():
    print("\n=================================================================")
    print("[2/3] MEMBUAT AUGMENTASI CITRA SENJA / SORE HARI (DUSK AERIAL)")
    print("=================================================================")

    # Ambil sampel citra yang mengandung manusia (civilian) dan jalan dari train
    train_imgs = list(TRAIN_IMG_DIR.glob("visdrone_*.jpg")) + list(TRAIN_IMG_DIR.glob("drone_*.jpg"))
    print(f"[*] Ditemukan {len(train_imgs)} citra aerial untuk diaugmentasi senja.")

    count_dusk = 0
    for img_path in train_imgs[:45]: # ambil 45 citra untuk senja
        lbl_path = TRAIN_LBL_DIR / (img_path.stem + ".txt")
        if not lbl_path.exists():
            continue

        # Baca citra asli
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        # 1. Reduksi pencahayaan senja (Gelap 40-55%)
        dusk_factor = np.random.uniform(0.45, 0.65)
        dusk_img = np.clip(img.astype(np.float32) * dusk_factor, 0, 255).astype(np.uint8)

        # 2. Nuansa warna senja (sedikit tint biru/oranye redup)
        b, g, r = cv2.split(dusk_img)
        b = np.clip(b.astype(np.float32) * 1.08, 0, 255).astype(np.uint8) # ambient skylight
        r = np.clip(r.astype(np.float32) * 0.95, 0, 255).astype(np.uint8)
        dusk_tinted = cv2.merge((b, g, r))

        # 3. Sedikit grain sensor malam (ISO noise)
        noise = np.random.normal(0, 3.5, dusk_tinted.shape).astype(np.float32)
        dusk_noisy = np.clip(dusk_tinted.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # Simpan ke dataset
        out_name = f"dusk_aug_{img_path.name}"
        target_img = TRAIN_IMG_DIR / out_name
        target_lbl = TRAIN_LBL_DIR / (Path(out_name).stem + ".txt")

        cv2.imwrite(str(target_img), dusk_noisy)
        target_lbl.write_text(lbl_path.read_text(encoding="utf-8"), encoding="utf-8")
        count_dusk += 1

    print(f"[*] Berhasil membuat {count_dusk} citra augmentasi senja/sore hari.")


def integrate_bonsai_into_dataset():
    print("\n=================================================================")
    print("[3/3] INTEGRASI BONSAI & POHON PANGKAS KE TAKSONOMI KELAS 9 (TREE)")
    print("=================================================================")

    bonsai_files = list(RAW_BONSAI_DIR.glob("*.jpg"))
    if not bonsai_files:
        print("[-] Tidak ada berkas bonsai untuk diproses.")
        return

    # Background template dari jalanan aerial / pekarangan
    bg_samples = list(TRAIN_IMG_DIR.glob("visdrone_*.jpg"))[:20]

    added_train = 0
    added_valid = 0

    for idx, b_path in enumerate(bonsai_files):
        b_img = cv2.imread(str(b_path))
        if b_img is None or b_img.shape[0] < 80 or b_img.shape[1] < 80:
            continue

        # Tentukan split
        is_val = (idx % 6 == 0)
        dest_img_dir = VALID_IMG_DIR if is_val else TRAIN_IMG_DIR
        dest_lbl_dir = VALID_LBL_DIR if is_val else TRAIN_LBL_DIR

        # Simpan citra langsung sebagai close-up bonsai / pohon pangkas
        # Normalisasi ke format standar 640x640
        h, w = b_img.shape[:2]
        pad_size = max(h, w)
        square = np.full((pad_size, pad_size, 3), 40, dtype=np.uint8) # latar gelap
        y_off = (pad_size - h) // 2
        x_off = (pad_size - w) // 2
        square[y_off:y_off + h, x_off:x_off + w] = b_img
        resized = cv2.resize(square, (640, 640))

        # Bounding box pohon/bonsai di tengah
        # YOLO format: class x_center y_center width height (normalized)
        x_c = 0.5
        y_c = 0.5
        bw = w / float(pad_size) * 0.92
        bh = h / float(pad_size) * 0.92
        yolo_line = f"9 {x_c:.6f} {y_c:.6f} {bw:.6f} {bh:.6f}\n"

        out_stem = f"bonsai_sample_{idx:03d}"
        dest_img = dest_img_dir / f"{out_stem}.jpg"
        dest_lbl = dest_lbl_dir / f"{out_stem}.txt"

        cv2.imwrite(str(dest_img), resized)
        dest_lbl.write_text(yolo_line, encoding="utf-8")

        # Buat juga versi dusk (senja)
        dusk_factor = 0.55
        resized_dusk = np.clip(resized.astype(np.float32) * dusk_factor, 0, 255).astype(np.uint8)
        dest_img_dusk = dest_img_dir / f"{out_stem}_dusk.jpg"
        dest_lbl_dusk = dest_lbl_dir / f"{out_stem}_dusk.txt"

        cv2.imwrite(str(dest_img_dusk), resized_dusk)
        dest_lbl_dusk.write_text(yolo_line, encoding="utf-8")

        if is_val:
            added_valid += 2
        else:
            added_train += 2

    print(f"[*] Berhasil mengintegrasikan bonsai ke kelas 9 (tree): +{added_train} train, +{added_valid} valid.")

    # Hapus cache lama agar YOLO membaca label baru secara bersih
    for split in ["train", "valid"]:
        cache_file = UNIFIED_DIR / split / "labels.cache"
        if cache_file.exists():
            cache_file.unlink()
            print(f"[*] Cache lama {cache_file.name} telah direset.")


if __name__ == "__main__":
    download_bonsai_images()
    create_dusk_augmented_samples()
    integrate_bonsai_into_dataset()
    print("\n[SUKSES] Dataset bonsai dan augmentasi senja selesai disiapkan 100%!")
