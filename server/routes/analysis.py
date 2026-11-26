"""
Module: server/routes/analysis.py
Deskripsi:
    Router FastAPI untuk analisis media offline (citra statis & video MP4/AVI):
    - Deteksi & klasifikasi taktis citra upload atau sampel uji (PNG, JPG, WebP)
    - Ekstraksi frame video, analisis berbasis sampling, dan deteksi temporal
    - Pengembalian citra beranotasi base64, keyframe snapshots, dan metadata JSON deteksi
"""

import cv2
import base64
import time
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from server.state import state
from server.auth import require_operator_role

router = APIRouter(
    prefix="/api/analysis",
    tags=["Media Analysis"],
    dependencies=[Depends(require_operator_role)],
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@router.get("/samples")
async def list_sample_media():
    """Mengembalikan daftar berkas foto dan video sampel uji di testbench_samples."""
    img_dir = BASE_DIR / "testbench_samples" / "images"
    vid_dir = BASE_DIR / "testbench_samples" / "videos"

    images = []
    if img_dir.exists():
        images = [f.name for f in img_dir.glob("*.*") if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]

    videos = []
    if vid_dir.exists():
        videos = [f.name for f in vid_dir.glob("*.mp4")]

    return {
        "images": sorted(images),
        "videos": sorted(videos)
    }


@router.post("/image")
async def analyze_image(
    file: Optional[UploadFile] = File(None),
    sample_filename: Optional[str] = Form(None),
    mode: str = Form("drone"),
    confidence_gate: float = Form(0.25),
    dusk_enhancer: bool = Form(False)
):
    """Menganalisis satu citra (upload atau sampel testbench) dan mengembalikan anotasi taktis."""
    try:
        img = None
        display_name_file = "sample.jpg"

        if sample_filename:
            sample_path = BASE_DIR / "testbench_samples" / "images" / sample_filename
            if not sample_path.exists():
                raise HTTPException(status_code=404, detail=f"Sampel citra '{sample_filename}' tidak ditemukan.")
            img = cv2.imread(str(sample_path))
            display_name_file = sample_filename
        elif file is not None:
            contents = await file.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            display_name_file = file.filename or "upload.jpg"
        else:
            raise HTTPException(status_code=400, detail="Pilih berkas foto atau nama sampel citra.")

        if img is None:
            raise HTTPException(status_code=400, detail="Berkas gambar tidak valid atau rusak")

        h, w = img.shape[:2]

        # Set confidence threshold pada detector
        state.detector.conf_threshold = confidence_gate

        # Inferensi AI Terpadu via TacticalDetector.detect()
        t0 = time.time()
        res = state.detector.detect(
            img,
            enable_distance=True,
            mode=mode,
            draw_hud_reticle=True,
            show_labels=True,
            enable_dusk=dusk_enhancer
        )
        infer_latency = round((time.time() - t0) * 1000.0, 1)

        annotated = res.get("annotated_frame", img)
        raw_dets = res.get("detections", [])
        hazard_count = res.get("hazard_count", 0)
        neutral_count = res.get("neutral_count", 0)
        threat_level = "RED SECTOR" if hazard_count > 0 else "GREEN SECTOR"
        threat_color_hex = "#FF3B30" if hazard_count > 0 else "#00FF66"

        valid_dets = []
        for idx, d in enumerate(raw_dets):
            cls_id = d.get("class_id", 0)
            info = state.threat_evaluator.get_info_by_class_id(cls_id)
            box = d.get("box", [0, 0, 0, 0])
            box_w = max(1.0, float(box[2] - box[0]))
            est_dist = state.distance_estimator.estimate_distance(box_w, class_id=cls_id)

            valid_dets.append({
                "id": idx + 1,
                "class_id": cls_id,
                "class_name": d.get("class_name", ""),
                "display_name": d.get("display_name", ""),
                "confidence": round(float(d.get("confidence", 0.0)), 2),
                "bbox": box,
                "threat": d.get("threat", "NEUTRAL"),
                "threat_label": d.get("threat_label", ""),
                "color_hex": info.get("color_hex", "#00FF66"),
                "estimated_distance_m": round(est_dist, 1) if est_dist else None
            })

        # Encode gambar teranotasi ke base64
        _, buf = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        b64_str = base64.b64encode(buf).decode('utf-8')
        annotated_data_url = f"data:image/jpeg;base64,{b64_str}"

        return {
            "success": True,
            "filename": display_name_file,
            "resolution": {"width": w, "height": h},
            "latency_ms": infer_latency,
            "mode": mode,
            "confidence_gate": confidence_gate,
            "dusk_enhancer": dusk_enhancer,
            "threat_summary": {
                "threat_level": threat_level,
                "threat_color_hex": threat_color_hex,
                "total_objects": len(valid_dets),
                "hazard_count": hazard_count,
                "neutral_count": neutral_count,
            },
            "detections": valid_dets,
            "annotated_image_url": annotated_data_url
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video")
async def analyze_video(
    file: Optional[UploadFile] = File(None),
    sample_filename: Optional[str] = Form(None),
    mode: str = Form("drone"),
    confidence_gate: float = Form(0.25),
    dusk_enhancer: bool = Form(False),
    sampling_interval: int = Form(6),
    max_frames: int = Form(200)
):
    """
    Menganalisis rekaman video offline (MP4/AVI) berbasis sampling frame temporal.
    Mengembalikan ringkasan statistik taktis, keyframe snapshot teranotasi, dan rincian log deteksi.
    """
    temp_path: Optional[str] = None
    video_source_path: Optional[str] = None
    display_name_file = "video.mp4"

    try:
        if sample_filename:
            s_path = BASE_DIR / "testbench_samples" / "videos" / sample_filename
            if not s_path.exists():
                raise HTTPException(status_code=404, detail=f"Sampel video '{sample_filename}' tidak ditemukan.")
            video_source_path = str(s_path)
            display_name_file = sample_filename
        elif file is not None:
            display_name_file = file.filename or "uploaded_video.mp4"
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            temp_path = tfile.name
            contents = await file.read()
            tfile.write(contents)
            tfile.close()
            video_source_path = temp_path
        else:
            raise HTTPException(status_code=400, detail="Pilih berkas video atau nama sampel video testbench.")

        cap = cv2.VideoCapture(video_source_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Gagal membuka berkas video rekaman.")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0 or np.isnan(fps):
            fps = 24.0
        vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_s = round(total_frames / fps, 1) if total_frames > 0 else 0.0

        # Inisialisasi detector & reset tracker untuk video baru
        state.detector.reset_tracker()
        state.detector.conf_threshold = confidence_gate

        t0 = time.time()
        frame_idx = 0
        sampled_count = 0
        hazard_count = 0
        neutral_count = 0

        drone_stats = {"soldier": 0, "civilian": 0, "military_vehicle": 0, "tree": 0}
        rov_stats = {"submarine": 0, "marine_life": 0, "coral_reef": 0, "diver": 0}

        detection_logs: List[Dict[str, Any]] = []
        keyframes: List[Dict[str, Any]] = []

        interval = max(1, sampling_interval)

        while cap.isOpened() and sampled_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if frame_idx % interval != 0:
                continue

            sampled_count += 1
            time_sec = round(frame_idx / fps, 1)

            res = state.detector.detect(
                frame,
                enable_distance=False,
                mode=mode,
                draw_hud_reticle=True,
                show_labels=True,
                enable_dusk=dusk_enhancer
            )

            frame_dets = res.get("detections", [])
            for d in frame_dets:
                cls_name = d.get("class_name", "")
                threat = d.get("threat", "NEUTRAL")

                if threat == "HAZARD":
                    hazard_count += 1
                else:
                    neutral_count += 1

                if cls_name in drone_stats:
                    drone_stats[cls_name] += 1
                if cls_name in rov_stats:
                    rov_stats[cls_name] += 1

                detection_logs.append({
                    "frame": frame_idx,
                    "timestamp_s": time_sec,
                    "class_name": cls_name,
                    "display_name": d.get("display_name", ""),
                    "confidence": round(float(d.get("confidence", 0.0)), 2),
                    "threat": threat,
                    "threat_label": d.get("threat_label", "")
                })

            # Ambil keyframe jika ada deteksi menarik (maksimal 6 keyframe snapshot)
            if frame_dets and len(keyframes) < 6:
                # Resize ringan agar response payload tidak terlalu besar
                annotated_f = res.get("annotated_frame", frame)
                thumb = cv2.resize(annotated_f, (640, 360))
                _, buf = cv2.imencode('.jpg', thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                b64_f = base64.b64encode(buf).decode('utf-8')
                keyframes.append({
                    "frame": frame_idx,
                    "timestamp_s": time_sec,
                    "target_count": len(frame_dets),
                    "targets": [d["display_name"] for d in frame_dets[:4]],
                    "image_url": f"data:image/jpeg;base64,{b64_f}"
                })

        cap.release()
        total_latency = round((time.time() - t0) * 1000.0, 1)

        threat_level = "RED SECTOR" if hazard_count > 0 else "GREEN SECTOR"
        threat_color_hex = "#FF3B30" if hazard_count > 0 else "#00FF66"

        return {
            "success": True,
            "filename": display_name_file,
            "duration_s": duration_s,
            "total_frames": total_frames,
            "sampled_frames": sampled_count,
            "fps": round(fps, 1),
            "resolution": {"width": vw, "height": vh},
            "latency_ms": total_latency,
            "mode": mode,
            "confidence_gate": confidence_gate,
            "threat_summary": {
                "threat_level": threat_level,
                "threat_color_hex": threat_color_hex,
                "total_detections": len(detection_logs),
                "hazard_count": hazard_count,
                "neutral_count": neutral_count,
                "drone_stats": drone_stats,
                "rov_stats": rov_stats
            },
            "keyframes": keyframes,
            "detection_log": detection_logs[:300]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
