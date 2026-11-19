"""
Script: scripts/enrich_trunks_soldiers_trees.py
Deskripsi:
    Pengayaan dataset komprehensif untuk mengatasi 3 isu klasifikasi:
    1. Civilian vs Soldier: Dataset pembeda spesifik prajurit bertaktis/kamuflase vs warga sipil pakaian kasual.
    2. Tree Trunks: Klasifikasi pohon mencakup batang pohon (trunk), tekstur kulit kayu (bark), dan hutan rimbun.
    3. Helikopter, Kendaraan, dan Bangunan: Memperkuat pemisahan helikopter/kendaraan (1) dan bangunan (10) dari pohon (9).
    4. Ekstraksi frame riil dari drone_forest_person_patrol.mp4 dan bonsai dataset lokal.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
import cv2
import numpy as np

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from ultralytics import YOLO

UNIFIED_DIR = base_dir / "data" / "unified_dataset"
TRAIN_IMG_DIR = UNIFIED_DIR / "train" / "images"
TRAIN_LBL_DIR = UNIFIED_DIR / "train" / "labels"
VALID_IMG_DIR = UNIFIED_DIR / "valid" / "images"
VALID_LBL_DIR = UNIFIED_DIR / "valid" / "labels"

RAW_DIR = base_dir / "data" / "raw_enrichment"
RAW_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "TacticalAISurveillanceBot/2.0 (student.project@gmail.com) Python-urllib/3.11"


def download_category_images(category_name: str, queries: list, max_images: int = 20):
    cat_dir = RAW_DIR / category_name
    cat_dir.mkdir(parents=True, exist_ok=True)

    existing_imgs = list(cat_dir.glob("*.jpg"))
    if len(existing_imgs) >= max_images:
        print(f"[*] Kategori {category_name} sudah memiliki {len(existing_imgs)} citra.")
        return existing_imgs[:max_images]

    print(f"[*] Mengunduh kategori: {category_name} ({len(queries)} queries, target {max_images})...")
    downloaded = len(existing_imgs)
    seen_urls = set()

    for q in queries:
        if downloaded >= max_images:
            break
        encoded_q = urllib.parse.quote(q)
        api_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={encoded_q}&gsrlimit=10&prop=pageimages&pithumbsize=800"
        req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
        try:
            time.sleep(1.0)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                pages = data.get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    if downloaded >= max_images:
                        break
                    thumb = pdata.get("thumbnail", {}).get("source")
                    if thumb and thumb not in seen_urls:
                        clean_url = thumb.split("?")[0].lower()
                        if clean_url.endswith((".jpg", ".jpeg", ".png")):
                            seen_urls.add(thumb)
                            out_file = cat_dir / f"{category_name}_{downloaded:03d}.jpg"
                            if not out_file.exists():
                                try:
                                    time.sleep(0.4)
                                    img_req = urllib.request.Request(thumb, headers={"User-Agent": USER_AGENT})
                                    with urllib.request.urlopen(img_req, timeout=10) as img_resp, open(out_file, "wb") as f_out:
                                        f_out.write(img_resp.read())

                                    test_img = cv2.imread(str(out_file))
                                    if test_img is None or test_img.shape[0] < 120 or test_img.shape[1] < 120:
                                        out_file.unlink(missing_ok=True)
                                    else:
                                        downloaded += 1
                                        print(f"  [+] [{category_name}] {downloaded}/{max_images}: {out_file.name}")
                                except Exception:
                                    pass
        except Exception as e:
            print(f"  [-] Query '{q}' gagal: {e}")

    print(f"[OK] Kategori {category_name} terkumpul {downloaded} citra.\n")
    return list(cat_dir.glob("*.jpg"))


def extract_vertical_tree_trunks(img_bgr: np.ndarray) -> list:
    """Mendeteksi batang pohon vertikal berdasarkan rasio aspek dan tekstur kontur kayu."""
    h, w = img_bgr.shape[:2]
    boxes = []

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_abs = np.uint8(np.absolute(sobel_x))
    _, thresh = cv2.threshold(sobel_abs, 35, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 30))
    morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect = bh / float(max(1, bw))
        area = bw * bh
        if aspect >= 1.6 and bh >= (h * 0.20) and area > (w * h * 0.015):
            xc = (x + bw / 2.0) / float(w)
            yc = (y + bh / 2.0) / float(h)
            nw = bw / float(w)
            nh = bh / float(h)
            boxes.append((xc, yc, nw, nh))

    if not boxes:
        boxes.append((0.50, 0.50, 0.60, 0.85))

    return boxes[:4]


def extract_video_frames(video_name: str, max_frames: int = 40):
    video_path = base_dir / "testbench_samples" / "videos" / video_name
    if not video_path.exists():
        return []

    print(f"[*] Mengekstrak {max_frames} frame dari {video_name}...")
    stem = Path(video_name).stem
    out_dir = RAW_DIR / f"{stem}_frames"
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    extracted = []

    step = max(1, total_frames // max_frames)
    for f_idx in range(10, total_frames - 5, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if ret and frame is not None:
            out_p = out_dir / f"{stem}_frame_{f_idx:04d}.jpg"
            cv2.imwrite(str(out_p), frame)
            extracted.append(out_p)

    cap.release()
    print(f"[OK] Berhasil mengekstrak {len(extracted)} frame dari {video_name}.\n")
    return extracted


def main():
    print("==========================================================")
    print("MEMULAI PENGAYAAN DATASET TAKTIS GCS (RETRAINING PREPARATION)")
    print("==========================================================")

    # 1. Ekstrak frame video nyata
    forest_frames = extract_video_frames("drone_forest_person_patrol.mp4", max_frames=50)
    drone_recon_frames = extract_video_frames("drone_land_recon.mp4", max_frames=25)

    # 2. Unduh citra spesifik dari web
    trunk_imgs = download_category_images(
        "tree_trunk",
        ["tree trunk", "tree bark", "bark (botany)", "forest tree trunks", "woodland tree trunks", "pine tree trunk", "birch tree trunk"],
        max_images=20
    )
    soldier_imgs = download_category_images(
        "soldier",
        ["soldier combat uniform", "infantry soldier camo", "marines military uniform", "tactical combat uniform soldier", "army soldier patrol"],
        max_images=20
    )
    civilian_imgs = download_category_images(
        "civilian",
        ["hiker on trail", "pedestrian walking park", "people walking park casual", "outdoor trail walker", "casual clothes pedestrian"],
        max_images=20
    )
    helicopter_imgs = download_category_images(
        "helicopter",
        ["military helicopter", "attack helicopter flight", "black hawk helicopter", "apache helicopter military", "military transport helicopter"],
        max_images=15
    )
    building_imgs = download_category_images(
        "building",
        ["military airfield hangar", "concrete warehouse exterior", "airfield hangar building", "industrial brick building", "military base building"],
        max_images=15
    )

    # 3. Muat bonsai lokal yang sudah ada
    bonsai_dir = base_dir / "data" / "raw_bonsai"
    local_bonsai_imgs = list(bonsai_dir.glob("*.jpg"))[:30]

    # 4. Muat model anotator
    print("[*] Memuat model annotator OpenImages & COCO...")
    coco_model = YOLO("yolov8n.pt")
    oiv7_model = YOLO("yolov8n-oiv7.pt")

    stats = {
        "tree_trunk": 0,
        "bonsai_local": 0,
        "soldier": 0,
        "civilian": 0,
        "helicopter": 0,
        "building": 0,
        "forest_frames": 0,
        "recon_frames": 0
    }

    def save_sample(img_bgr, labels, stem, is_valid=False):
        if not labels:
            return
        target_img_dir = VALID_IMG_DIR if is_valid else TRAIN_IMG_DIR
        target_lbl_dir = VALID_LBL_DIR if is_valid else TRAIN_LBL_DIR

        dest_img = target_img_dir / f"{stem}.jpg"
        dest_lbl = target_lbl_dir / f"{stem}.txt"

        resized = cv2.resize(img_bgr, (640, 640))
        cv2.imwrite(str(dest_img), resized)
        with open(dest_lbl, "w", encoding="utf-8") as f:
            f.write("\n".join(labels) + "\n")

    # A. Anotasi Batang Pohon Web (tree_trunk) -> Kelas 9 (tree)
    for idx, p in enumerate(trunk_imgs):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []
        res = oiv7_model.predict(img, conf=0.20, verbose=False)
        for box in res[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c in {553, 364, 112, 393}:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"9 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")

        trunks = extract_vertical_tree_trunks(img)
        for xc, yc, nw, nh in trunks:
            labels.append(f"9 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}")

        is_val = (idx % 5 == 0)
        stem = f"enrich_trunk_{p.stem}"
        save_sample(img, labels, stem, is_valid=is_val)
        stats["tree_trunk"] += 1

    # B. Anotasi Batang Pohon Bonsai Lokal -> Kelas 9 (tree)
    for idx, p in enumerate(local_bonsai_imgs):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []
        res = oiv7_model.predict(img, conf=0.18, verbose=False)
        for box in res[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c in {553, 364, 112, 393, 258}: # Tree, plant, houseplant
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"9 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")
        if not labels:
            labels.append("9 0.500000 0.500000 0.700000 0.800000")

        is_val = (idx % 5 == 0)
        stem = f"enrich_bonsai_trunk_{p.stem}"
        save_sample(img, labels, stem, is_valid=is_val)
        stats["bonsai_local"] += 1

    # C. Anotasi Prajurit (soldier) -> Kelas 0 (soldier)
    for idx, p in enumerate(soldier_imgs):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []
        res = coco_model.predict(img, conf=0.25, verbose=False)
        for box in res[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c == 0:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"0 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")
        if not labels:
            labels.append("0 0.500000 0.500000 0.500000 0.850000")

        is_val = (idx % 5 == 0)
        stem = f"enrich_soldier_{p.stem}"
        save_sample(img, labels, stem, is_valid=is_val)
        stats["soldier"] += 1

    # D. Anotasi Sipil (civilian) -> Kelas 2 (civilian)
    for idx, p in enumerate(civilian_imgs):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []
        res = coco_model.predict(img, conf=0.25, verbose=False)
        for box in res[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c == 0:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"2 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")
        if not labels:
            labels.append("2 0.500000 0.500000 0.500000 0.850000")

        is_val = (idx % 5 == 0)
        stem = f"enrich_civilian_{p.stem}"
        save_sample(img, labels, stem, is_valid=is_val)
        stats["civilian"] += 1

    # E. Anotasi Helikopter / Kendaraan Tempur -> Kelas 1 (military_vehicle)
    for idx, p in enumerate(helicopter_imgs):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []
        res_oi = oiv7_model.predict(img, conf=0.20, verbose=False)
        for box in res_oi[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c in {247, 302, 549, 90, 572}:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"1 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")
        if not labels:
            labels.append("1 0.500000 0.500000 0.750000 0.600000")

        is_val = (idx % 5 == 0)
        stem = f"enrich_heli_{p.stem}"
        save_sample(img, labels, stem, is_valid=is_val)
        stats["helicopter"] += 1

    # F. Anotasi Bangunan -> Kelas 10 (building)
    for idx, p in enumerate(building_imgs):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []
        res_oi = oiv7_model.predict(img, conf=0.20, verbose=False)
        for box in res_oi[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c in {70, 257, 354}:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"10 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")
        if not labels:
            labels.append("10 0.500000 0.500000 0.850000 0.700000")

        is_val = (idx % 5 == 0)
        stem = f"enrich_bldg_{p.stem}"
        save_sample(img, labels, stem, is_valid=is_val)
        stats["building"] += 1

    # G. Anotasi Frame Hutan Nyata (drone_forest_person_patrol.mp4)
    # Orang berpakaian kasual (2: civilian), pohon (9: tree), dan batang pohon (9: tree)
    for idx, p in enumerate(forest_frames):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []

        res_coco = coco_model.predict(img, conf=0.22, verbose=False)
        for box in res_coco[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c == 0:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"2 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")

        res_oi = oiv7_model.predict(img, conf=0.18, verbose=False)
        for box in res_oi[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c in {553, 364, 112, 393}:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"9 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")

        trunks = extract_vertical_tree_trunks(img)
        for xc, yc, nw, nh in trunks:
            labels.append(f"9 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}")

        is_val = (idx % 5 == 0)
        stem = f"enrich_forest_{p.stem}"
        save_sample(img, labels, stem, is_valid=is_val)
        stats["forest_frames"] += 1

    # H. Anotasi Frame Recon Nyata (drone_land_recon.mp4)
    # Helikopter & kendaraan (1: military_vehicle) dan bangunan (10: building)
    for idx, p in enumerate(drone_recon_frames):
        img = cv2.imread(str(p))
        if img is None:
            continue
        labels = []

        res_oi = oiv7_model.predict(img, conf=0.20, verbose=False)
        for box in res_oi[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c in {247, 302, 549, 90, 572}:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"1 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")
            elif c in {70, 257, 354}:
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"10 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")

        res_coco = coco_model.predict(img, conf=0.20, verbose=False)
        for box in res_coco[0].boxes:
            c = int(box.cls[0].cpu().numpy())
            if c in [2, 4, 5, 7]: # car, airplane, bus, truck -> military_vehicle
                xywh = box.xywhn[0].cpu().numpy()
                labels.append(f"1 {xywh[0]:.6f} {xywh[1]:.6f} {xywh[2]:.6f} {xywh[3]:.6f}")

        if labels:
            is_val = (idx % 5 == 0)
            stem = f"enrich_recon_{p.stem}"
            save_sample(img, labels, stem, is_valid=is_val)
            stats["recon_frames"] += 1

    print("\n==========================================================")
    print("HASIL PENGAYAAN DATASET TERPADU SELESAI:")
    for k, v in stats.items():
        print(f"  • {k:15}: +{v} sampel citra")
    print("==========================================================")


if __name__ == "__main__":
    main()
