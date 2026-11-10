"""
Module: core/detector.py
Deskripsi:
    Engine deteksi objek & klasifikasi taktis menggunakan Ultralytics YOLOv8 / YOLO11.
    Mendukung 2-Stage Pipeline (Stage 1 Localization + Stage 2 Soldier Team Affiliation),
    menghasilkan bounding box, label kelas, confidence score, status ancaman, dan estimasi jarak.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

from core.threat_evaluator import ThreatEvaluator
from core.distance_estimator import DistanceEstimator


class TacticalDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: str = "cpu"
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.distance_estimator = DistanceEstimator()
        self.model = None
        self.model_loaded = False

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> Tuple[bool, str]:
        """Memuat model bobot YOLO (.pt)."""
        if not YOLO_AVAILABLE:
            return False, "Library 'ultralytics' belum terinstal. Silakan jalankan: pip install ultralytics"

        path_obj = Path(model_path)
        try:
            self.model = YOLO(str(path_obj))
            self.model_loaded = True
            return True, f"Model berhasil dimuat dari: {path_obj.name}"
        except Exception as e:
            self.model_loaded = False
            return False, f"Gagal memuat model: {str(e)}"

    def detect(
        self,
        frame: np.ndarray,
        enable_distance: bool = True
    ) -> Dict[str, Any]:
        """
        Melakukan inferensi deteksi objek pada satu frame citra.
        """
        annotated_frame = frame.copy()
        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []

        if not self.model_loaded or self.model is None:
            cv2.putText(
                annotated_frame,
                "Model AI Belum Dimuat",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 165, 255),
                2
            )
            return {
                "annotated_frame": annotated_frame,
                "detections": [],
                "environment": "Tidak Aktif",
                "hazard_count": 0,
                "neutral_count": 0
            }

        # Jalankan inferensi YOLO (Stage 1)
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False
        )

        detected_class_ids = []
        hazard_count = 0
        neutral_count = 0

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())

                detected_class_ids.append(cls_id)
                info = ThreatEvaluator.get_info_by_class_id(cls_id)

                x1, y1, x2, y2 = xyxy
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                box_width = float(x2 - x1)

                display_name = info["display"]
                threat_label = info["threat_label"]
                color_bgr = info["color_bgr"]

                # STAGE 2: Jika objek adalah prajurit (cls_id == 0), klasifikasikan Tim A vs Tim B
                if cls_id == 0 and (x2 - x1) > 10 and (y2 - y1) > 10:
                    soldier_crop = frame[y1:y2, x1:x2]
                    t_name, t_label, t_bgr, _ = ThreatEvaluator.classify_soldier_team(soldier_crop)
                    display_name = t_name
                    threat_label = t_label
                    color_bgr = t_bgr

                # Estimasi Jarak
                est_dist = None
                if enable_distance:
                    est_dist = self.distance_estimator.estimate_distance(
                        pixel_width=box_width,
                        class_id=cls_id
                    )

                is_hazard = (info["threat"] == "HAZARD")
                if is_hazard:
                    hazard_count += 1
                else:
                    neutral_count += 1

                det_item = {
                    "class_id": cls_id,
                    "class_name": info["name"],
                    "display_name": display_name,
                    "confidence": conf,
                    "box": [int(x1), int(y1), int(x2), int(y2)],
                    "threat": info["threat"],
                    "threat_label": threat_label,
                    "distance_m": est_dist,
                    "color_bgr": color_bgr
                }
                detections.append(det_item)

                # Visualisasi Bounding Box & Telemetri OSD
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color_bgr, 2)

                label_text = f"{display_name} {int(conf * 100)}%"
                if est_dist is not None:
                    label_text += f" | {est_dist}m"

                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(
                    annotated_frame,
                    (x1, max(0, y1 - 20)),
                    (x1 + tw + 6, max(0, y1)),
                    color_bgr,
                    -1
                )
                cv2.putText(
                    annotated_frame,
                    label_text,
                    (x1 + 3, max(14, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )

        env_domain, _ = ThreatEvaluator.determine_environment(detected_class_ids)

        return {
            "annotated_frame": annotated_frame,
            "detections": detections,
            "environment": env_domain,
            "hazard_count": hazard_count,
            "neutral_count": neutral_count
        }

