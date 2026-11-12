"""
Script: scripts/generate_synthetic_test_videos.py
Deskripsi:
    Membuat 2 berkas video simulasi realistis berformat MP4 di folder testbench_samples/videos/:
    1. rov_underwater_patrol.mp4 (Skenario Bawah Air: Kapal Selam, Biota Laut, Terumbu Karang)
    2. drone_land_recon.mp4 (Skenario Darat: Prajurit Bersenjata, Tank Tempur, Warga Sipil)
    Dilengkapi simulasi pergerakan panning kamera dan OSD telemetri wahana.
"""

import cv2
import numpy as np
from pathlib import Path

def create_video_from_images(
    images,
    output_path: Path,
    fps: int = 20,
    duration_per_image: float = 3.5,
    overlay_type: str = "rov"
):
    if not images:
        print(f"[SKIP] Tidak ada gambar untuk {output_path.name}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_w, target_h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (target_w, target_h))

    total_frames_per_img = int(fps * duration_per_image)
    frame_counter = 0

    print(f"[*] Membuat video: {output_path.name} ({len(images)} klip adegan)...")

    for img_idx, img_p in enumerate(images):
        raw_bgr = cv2.imread(str(img_p))
        if raw_bgr is None:
            continue

        raw_bgr = cv2.resize(raw_bgr, (target_w + 120, target_h + 80))

        # Efek pergerakan kamera (Pan / Drift)
        for f in range(total_frames_per_img):
            frame_counter += 1
            progress = f / float(total_frames_per_img)

            # Simulasi pergeseran koordinat (Drifting Camera Motion)
            offset_x = int(60 * progress)
            offset_y = int(40 * np.sin(progress * np.pi))

            frame = raw_bgr[offset_y : offset_y + target_h, offset_x : offset_x + target_w].copy()

            # Tambahkan OSD Telemetri Taktis
            timestamp = f"T+{(frame_counter / fps):05.1f}s"

            if overlay_type == "rov":
                depth = 14.5 + 2.0 * np.sin(frame_counter * 0.05)
                heading = int((120 + frame_counter * 0.2) % 360)
                osd_text = f"ROV DEEP-SURV // DEPTH: {depth:.1f}m // HDG: {heading:03d} // {timestamp}"
                cv2.putText(frame, osd_text, (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.rectangle(frame, (30, 25), (780, 65), (0, 255, 255), 1)
            else:
                alt = 45.0 + 3.0 * np.cos(frame_counter * 0.04)
                spd = 18.2 + 1.5 * np.sin(frame_counter * 0.08)
                osd_text = f"DRONE FPV-RECON // ALT: {alt:.1f}m // SPD: {spd:.1f}km/h // {timestamp}"
                cv2.putText(frame, osd_text, (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 255), 2, cv2.LINE_AA)
                cv2.rectangle(frame, (30, 25), (820, 65), (0, 230, 255), 1)

            out.write(frame)

    out.release()
    print(f"[OK] Selesai: {output_path} (Ukuran: {output_path.stat().st_size / (1024*1024):.2f} MB)")

def main():
    base_dir = Path(__file__).resolve().parent.parent
    test_img_dir = base_dir / "data" / "unified_dataset" / "test" / "images"
    videos_dir = base_dir / "testbench_samples" / "videos"

    all_test_imgs = list(test_img_dir.glob("*.*"))

    # Pisahkan citra bawah air dan citra darat berdasarkan prefix dataset
    underwater_imgs = [p for p in all_test_imgs if p.name.startswith("ds1_") or p.name.startswith("ds2_") or p.name.startswith("ds6_")][:8]
    land_imgs = [p for p in all_test_imgs if p.name.startswith("ds3_") or p.name.startswith("ds4_") or p.name.startswith("ds5_")][:8]

    # 1. Video ROV Bawah Air
    rov_path = videos_dir / "rov_underwater_patrol.mp4"
    create_video_from_images(underwater_imgs, rov_path, overlay_type="rov")

    # 2. Video Drone Darat FPV
    drone_path = videos_dir / "drone_land_recon.mp4"
    create_video_from_images(land_imgs, drone_path, overlay_type="drone")

if __name__ == "__main__":
    main()
