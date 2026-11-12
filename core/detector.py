"""
Module: core/detector.py
Deskripsi:
    Engine deteksi objek & klasifikasi taktis menggunakan Ultralytics YOLOv8 / YOLO11.
    Mendukung Mode Operasi Terpisah:
    - Mode ROV (Danau, Eksplorasi & Games Bawah Air)
    - Mode Drone (Pemantauan Udara, Spectator Tim A vs Tim B)
    Dilengkapi Tactical HUD Reticles & Telemetri Real-time.
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
        if not YOLO_AVAILABLE:
            return False, "Library 'ultralytics' belum terinstal."

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
        enable_distance: bool = True,
        mode: str = "all",
        draw_hud_reticle: bool = True
    ) -> Dict[str, Any]:
        """
        Melakukan inferensi taktis dengan pemfilteran mode:
        - mode='rov': Menampilkan target danau/bawah air (Submarine, Ikan, Karang, ROV, Kapal)
        - mode='drone': Menampilkan target udara/darat (Soldier Tim A/B, Kendaraan, Sipil, Kapal)
        - mode='all': Menampilkan semua target
        """
        annotated_frame = frame.copy()
        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []

        # Data Counter Khusus Mode
        drone_stats = {"team_a": 0, "team_b": 0, "civilian": 0, "military_vehicle": 0}
        rov_stats = {"submarine": 0, "marine_life": 0, "coral_reef": 0, "rov": 0, "ship": 0}

        if not self.model_loaded or self.model is None:
            cv2.putText(
                annotated_frame,
                "TACTICAL AI CORE OFFLINE",
                (40, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2
            )
            return {
                "annotated_frame": annotated_frame,
                "detections": [],
                "environment": "Offline",
                "hazard_count": 0,
                "neutral_count": 0,
                "drone_stats": drone_stats,
                "rov_stats": rov_stats
            }

        # Tambahkan Frame HUD Taktis di Sudut Layar
        if draw_hud_reticle:
            self._draw_tactical_hud_overlay(annotated_frame, mode)

        # Jalankan inferensi YOLO
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

                # FILTER BERDASARKAN MODE OPERASI (ROV vs DRONE)
                if not ThreatEvaluator.is_class_allowed_for_mode(cls_id, mode):
                    continue

                detected_class_ids.append(cls_id)
                info = ThreatEvaluator.get_info_by_class_id(cls_id)

                x1, y1, x2, y2 = xyxy
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                box_width = float(x2 - x1)

                display_name = info["display"]
                threat_label = info["threat_label"]
                color_bgr = info["color_bgr"]

                # STAGE 2: Pembedaan Soldier Tim A vs Tim B (Khusus Drone / Spectator)
                if cls_id == 0 and (x2 - x1) > 10 and (y2 - y1) > 10:
                    soldier_crop = frame[y1:y2, x1:x2]
                    t_name, t_label, t_bgr, _ = ThreatEvaluator.classify_soldier_team(soldier_crop)
                    display_name = t_name
                    threat_label = t_label
                    color_bgr = t_bgr
                    if "TIM A" in t_name:
                        drone_stats["team_a"] += 1
                    else:
                        drone_stats["team_b"] += 1
                elif cls_id == 1:
                    drone_stats["military_vehicle"] += 1
                elif cls_id == 2:
                    drone_stats["civilian"] += 1
                elif cls_id == 3:
                    rov_stats["ship"] += 1
                elif cls_id == 4:
                    rov_stats["submarine"] += 1
                elif cls_id == 5:
                    rov_stats["marine_life"] += 1
                elif cls_id == 6:
                    rov_stats["coral_reef"] += 1
                elif cls_id == 7:
                    rov_stats["rov"] += 1

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

                # Gambar Corner Reticle Bounding Box Taktis
                self._draw_tactical_bbox(annotated_frame, x1, y1, x2, y2, color_bgr, display_name, conf, est_dist)

        env_domain, _ = ThreatEvaluator.determine_environment(detected_class_ids, mode=mode)

        return {
            "annotated_frame": annotated_frame,
            "detections": detections,
            "environment": env_domain,
            "hazard_count": hazard_count,
            "neutral_count": neutral_count,
            "drone_stats": drone_stats,
            "rov_stats": rov_stats
        }

    @staticmethod
    def _draw_tactical_bbox(frame, x1, y1, x2, y2, color, label, conf, distance):
        """Menggambar bounding box bergaya Tactical Corner Reticle (bidik tempur)."""
        box_w = x2 - x1
        box_h = y2 - y1
        corner_len = int(min(box_w, box_h) * 0.25)
        thickness = 2

        # 4 Sudut Taktis
        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, thickness)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, thickness)
        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, thickness)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, thickness)
        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, thickness)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, thickness)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, thickness)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, thickness)

        # Garis tipis kotak luar
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

        # Teks OSD Taktis
        osd_text = f"TARGET: {label} [{int(conf * 100)}%]"
        if distance is not None:
            osd_text += f" // RNG: {distance}m"

        (tw, th), _ = cv2.getTextSize(osd_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        # Background badge gelap
        cv2.rectangle(frame, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(0, y1)), (10, 14, 23), -1)
        cv2.rectangle(frame, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(0, y1)), color, 1)
        cv2.putText(frame, osd_text, (x1 + 3, max(13, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)

    @staticmethod
    def _draw_tactical_hud_overlay(frame, mode: str):
        """Menggambar crosshair dan garis telemetri taktis pada frame."""
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        hud_color = (0, 229, 255) if mode == "rov" else (0, 255, 102)

        # Center Crosshair
        cv2.line(frame, (cx - 25, cy), (cx + 25, cy), hud_color, 1)
        cv2.line(frame, (cx, cy - 25), (cx, cy + 25), hud_color, 1)
        cv2.circle(frame, (cx, cy), 12, hud_color, 1)

        # 4 Sudut Layar Utama
        border_len = 35
        # Top-Left
        cv2.line(frame, (20, 20), (20 + border_len, 20), hud_color, 2)
        cv2.line(frame, (20, 20), (20, 20 + border_len), hud_color, 2)
        # Top-Right
        cv2.line(frame, (w - 20, 20), (w - 20 - border_len, 20), hud_color, 2)
        cv2.line(frame, (w - 20, 20), (w - 20, 20 + border_len), hud_color, 2)
        # Bottom-Left
        cv2.line(frame, (20, h - 20), (20 + border_len, h - 20), hud_color, 2)
        cv2.line(frame, (20, h - 20), (20, h - 20 - border_len), hud_color, 2)
        # Bottom-Right
        cv2.line(frame, (w - 20, h - 20), (w - 20 - border_len, h - 20), hud_color, 2)
        cv2.line(frame, (w - 20, h - 20), (w - 20, h - 20 - border_len), hud_color, 2)
