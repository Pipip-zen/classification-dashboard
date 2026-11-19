"""
Module: server/routes/analysis.py
Deskripsi:
    Router FastAPI untuk analisis media offline (citra statis & video):
    - Deteksi & klasifikasi taktis citra upload (PNG, JPG, WebP)
    - Ekstraksi frame video & analisis berbasis sampling
    - Pengembalian citra beranotasi base64 & metadata JSON deteksi
"""

import cv2
import base64
import time
import numpy as np
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from server.state import state

router = APIRouter(prefix="/api/analysis", tags=["Media Analysis"])


@router.post("/image")
async def analyze_image(
    file: UploadFile = File(...),
    mode: str = Form("drone"),
    confidence_gate: float = Form(0.25),
    dusk_enhancer: bool = Form(False)
):
    """Menganalisis satu citra upload dan mengembalikan anotasi serta telemetri taktis."""
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
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

        # Enrich dengan estimasi jarak pinhole & color_hex
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
            "filename": file.filename,
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
