"""
Module: core/detector.py
Deskripsi:
    Engine deteksi objek & klasifikasi taktis menggunakan Ultralytics YOLOv8 / YOLO11.
    FOKUS MURNI IMAGE CLASSIFICATION & OBJECT DETECTION:
    - Mode ROV (Danau & Bawah Air: Kapal Selam, Biota, Karang, ROV, Kapal)
    - Mode Drone (POV Umum):
        * Orang -> Pembedaan Warna Baju: Tim A (Biru) vs Tim B (Ungu) vs Sipil (Lainnya)
        * Kendaraan / Vehicle (Kendaraan umum dengan filter anti-besi/bebatuan)
        * Perahu / Kapal Danau
        * Drone FPV
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

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from core.threat_evaluator import ThreatEvaluator


class TacticalDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: Optional[str] = None
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.model_path = model_path
        self._last_mtime: Optional[float] = None
        
        # Auto-detect GPU CUDA jika tersedia
        if device is None:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                self.device = "0"
            else:
                self.device = "cpu"
        else:
            self.device = device

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
            self.model_path = str(path_obj)
            if path_obj.exists():
                self._last_mtime = path_obj.stat().st_mtime
            return True, f"Model berhasil dimuat dari: {path_obj.name}"
        except Exception as e:
            self.model_loaded = False
            return False, f"Gagal memuat model: {str(e)}"

    def detect(
        self,
        frame: np.ndarray,
        enable_distance: bool = False,
        mode: str = "all",
        draw_hud_reticle: bool = True,
        enable_clahe: bool = False
    ) -> Dict[str, Any]:
        """
        Melakukan inferensi taktis berfokus murni pada Image Classification & Localization:
        - mode='rov': Menampilkan target danau/bawah air (Submarine, Ikan, Karang, ROV, Kapal, Diver)
        - mode='drone': Menampilkan target POV umum (Soldier, Civilian, Vehicle, Kapal, Tree, Building, FPV)
        - enable_clahe: Toggle real-time underwater CLAHE enhancer (sesuai kebutuhan video)
        """
        # Hot-reloading jika file bobot model di disk diperbarui
        if self.model_path:
            p = Path(self.model_path)
            if p.exists() and self._last_mtime is not None:
                try:
                    curr_mtime = p.stat().st_mtime
                    if curr_mtime > self._last_mtime:
                        self.load_model(self.model_path)
                except Exception:
                    pass

        annotated_frame = frame.copy()
        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []

        drone_stats = {
            "soldier": 0,
            "civilian": 0,
            "military_vehicle": 0,
            "tree": 0,
            "building": 0,
            "fpv_drone": 0
        }
        rov_stats = {"submarine": 0, "marine_life": 0, "coral_reef": 0, "rov": 0, "ship": 0, "diver": 0}

        # Real-time Underwater Vision Enhancer (Dapat diaktifkan via toggle untuk video keruh)
        if enable_clahe and mode.lower() in ["rov", "all"]:
            infer_frame = self.enhance_underwater_frame(frame)
            annotated_frame = infer_frame.copy()
        else:
            infer_frame = frame
            annotated_frame = frame.copy()

        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []

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

        # Frame HUD Taktis di Sudut Layar
        if draw_hud_reticle:
            self._draw_tactical_hud_overlay(annotated_frame, mode)

        # Jalankan inferensi YOLO
        results = self.model.predict(
            source=infer_frame,
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

                # FILTER 1: FILTER BERDASARKAN MODE OPERASI (ROV vs DRONE)
                if not ThreatEvaluator.is_class_allowed_for_mode(cls_id, mode):
                    continue

                x1, y1, x2, y2 = xyxy
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                box_w = x2 - x1
                box_h = y2 - y1

                # FILTER 2: AMBANG BATAS KHUSUS KENDARAAN (ADAPTIF UNTUK DRONE KETINGGIAN TINGGI)
                if cls_id == 1:
                    min_area = 150 if mode.lower() == "drone" else 500
                    if (box_w * box_h) < min_area:
                        continue # Abaikan noise artefak sangat kecil (< 150 px)

                # FILTER 3: SANITASI KLASIFIKASI BAWAH AIR (ANTI-MISKLASIFIKASI SUBMARINE PADA IKAN)
                if mode.lower() in ["rov", "all"]:
                    cls_id = ThreatEvaluator.sanitize_underwater_target(
                        class_id=cls_id,
                        box_w=box_w,
                        box_h=box_h,
                        frame_w=w,
                        frame_h=h,
                        conf=conf
                    )

                detected_class_ids.append(cls_id)
                info = ThreatEvaluator.get_info_by_class_id(cls_id)

                display_name = info["display"]
                threat_label = info["threat_label"]
                color_bgr = info["color_bgr"]
                threat_status = info["threat"]

                # PENCATATAN STATISTIK TAKTIS BERDASARKAN KELAS MURNI (TANPA OVERRIDE WARNA BAJU)
                if cls_id == 0:
                    drone_stats["soldier"] += 1
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
                elif cls_id == 8:
                    drone_stats["fpv_drone"] += 1
                elif cls_id == 9:
                    drone_stats["tree"] += 1
                elif cls_id == 10:
                    drone_stats["building"] += 1
                elif cls_id == 11:
                    rov_stats["diver"] += 1

                is_hazard = (threat_status == "HAZARD")
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
                    "threat": threat_status,
                    "threat_label": threat_label,
                    "color_bgr": color_bgr
                }
                detections.append(det_item)

                # Gambar Corner Reticle Bounding Box Taktis
                self._draw_tactical_bbox(annotated_frame, x1, y1, x2, y2, color_bgr, display_name, conf)

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
    def _draw_tactical_bbox(frame, x1, y1, x2, y2, color, label, conf):
        """Menggambar bounding box bergaya Tactical Corner Reticle."""
        box_w = x2 - x1
        box_h = y2 - y1
        corner_len = int(min(box_w, box_h) * 0.25)
        thickness = 2

        # 4 Sudut Taktis
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, thickness)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, thickness)
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, thickness)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, thickness)
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, thickness)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, thickness)
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, thickness)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, thickness)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

        # Label Klasifikasi & Confidence Murni
        osd_text = f"{label} [{int(conf * 100)}%]"

        (tw, th), _ = cv2.getTextSize(osd_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(frame, (x1, max(0, y1 - 22)), (x1 + tw + 6, max(0, y1)), (10, 14, 23), -1)
        cv2.rectangle(frame, (x1, max(0, y1 - 22)), (x1 + tw + 6, max(0, y1)), color, 1)
        cv2.putText(frame, osd_text, (x1 + 3, max(14, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    @staticmethod
    def _draw_tactical_hud_overlay(frame, mode: str):
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        hud_color = (0, 229, 255) if mode == "rov" else (0, 255, 102)

        # Center Crosshair
        cv2.line(frame, (cx - 25, cy), (cx + 25, cy), hud_color, 1)
        cv2.line(frame, (cx, cy - 25), (cx, cy + 25), hud_color, 1)
        cv2.circle(frame, (cx, cy), 12, hud_color, 1)

        # 4 Sudut Layar
        border_len = 35
        cv2.line(frame, (20, 20), (20 + border_len, 20), hud_color, 2)
        cv2.line(frame, (20, 20), (20, 20 + border_len), hud_color, 2)
        cv2.line(frame, (w - 20, 20), (w - 20 - border_len, 20), hud_color, 2)
        cv2.line(frame, (w - 20, 20), (w - 20, 20 + border_len), hud_color, 2)
        cv2.line(frame, (20, h - 20), (20 + border_len, h - 20), hud_color, 2)
        cv2.line(frame, (20, h - 20), (20, h - 20 - border_len), hud_color, 2)
        cv2.line(frame, (w - 20, h - 20), (w - 20 - border_len, h - 20), hud_color, 2)
        cv2.line(frame, (w - 20, h - 20), (w - 20, h - 20 - border_len), hud_color, 2)

    @staticmethod
    def enhance_underwater_frame(frame: np.ndarray) -> np.ndarray:
        """
        Real-time Underwater Vision Enhancer (CLAHE + Color Balance).
        Mengeliminasi kekeruhan/kabut hijau dan menajamkan kontras terumbu karang,
        biota laut, dan penyelam agar deteksi lebih tajam dan confidence >= 80%.
        """
        if frame is None or frame.size == 0:
            return frame

        # Konversi ke LAB Color Space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)

        # CLAHE adaptif pada Lightness channel
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        cl = clahe.apply(l_chan)

        # Re-balance kanal warna agar tidak terlalu hijau kusam
        a_balanced = cv2.addWeighted(a_chan, 1.08, np.full_like(a_chan, 128), -0.08, 0)

        enhanced_lab = cv2.merge((cl, a_balanced, b_chan))
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
