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
import threading
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
from core.temporal_tracker import TemporalTracker


class TacticalDetector:
    # Ambang batas proteksi minimum per kelas (mencegah noise sporadis pada confidence rendah)
    CLASS_CONFIDENCE_FLOOR = {
        0: 0.20,  # soldier / kombatan
        1: 0.20,  # military_vehicle / kendaraan umum
        2: 0.20,  # civilian / pejalan kaki / pengendara
        3: 0.15,  # tree / kanopi vegetasi & batang
        4: 0.20,  # submarine
        5: 0.18,  # marine_life
        6: 0.18,  # coral_reef
        7: 0.20   # diver / penyelam
    }

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
        self._infer_lock = threading.Lock()
        self.tracker = TemporalTracker(iou_threshold=0.35, max_age=15)

        if model_path:
            self.load_model(model_path)

    def reset_tracker(self):
        """Mereset riwayat tracking temporal saat berganti stream/video."""
        self.tracker = TemporalTracker(iou_threshold=0.35, max_age=15)

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
        enable_clahe: bool = False,
        show_labels: bool = True,
        enable_dusk: bool = False,
        tracker: Optional[TemporalTracker] = None,
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Melakukan inferensi taktis berfokus murni pada Image Classification & Localization.
        Mendukung tracker dan conf_threshold per-channel agar aman dipakai paralel.
        """
        annotated_frame = frame.copy()
        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []
        active_conf = float(conf_threshold) if conf_threshold is not None else self.conf_threshold
        active_tracker = tracker if tracker is not None else self.tracker

        drone_stats = {
            "soldier": 0,
            "military_vehicle": 0,
            "civilian": 0,
            "tree": 0
        }
        rov_stats = {"submarine": 0, "marine_life": 0, "coral_reef": 0, "diver": 0}

        # Real-time Vision Enhancer (Underwater CLAHE vs Aerial Dusk/Low-Light)
        if enable_clahe and mode.lower() in ["rov", "all"]:
            infer_frame = self.enhance_underwater_frame(frame)
            annotated_frame = infer_frame.copy()
        elif enable_dusk and mode.lower() in ["drone", "all"]:
            infer_frame = self.enhance_dusk_frame(frame)
            annotated_frame = infer_frame.copy()
        else:
            infer_frame = frame
            annotated_frame = frame.copy()

        # Frame HUD Taktis di Sudut Layar
        if draw_hud_reticle:
            self._draw_tactical_hud_overlay(annotated_frame, mode)

        # Kunci akses model agar inferensi antar-channel dan hot-reload tetap thread-safe
        with self._infer_lock:
            if self.model_path:
                p = Path(self.model_path)
                if p.exists() and self._last_mtime is not None:
                    try:
                        curr_mtime = p.stat().st_mtime
                        if curr_mtime > self._last_mtime:
                            self.load_model(self.model_path)
                    except Exception:
                        pass

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

            results = self.model.predict(
                source=infer_frame,
                conf=min(active_conf, 0.15),
                iou=0.35,
                agnostic_nms=True,
                device=self.device,
                verbose=False
            )

        detected_class_ids = []
        hazard_count = 0
        neutral_count = 0
        raw_candidates = []

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())

                if not ThreatEvaluator.is_class_allowed_for_mode(cls_id, mode):
                    continue

                min_floor = self.CLASS_CONFIDENCE_FLOOR.get(cls_id, 0.20)
                effective_conf = max(active_conf, min_floor)
                if conf < effective_conf:
                    continue

                x1, y1, x2, y2 = xyxy
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                box_w = x2 - x1
                box_h = y2 - y1

                # FILTER 3: AMBANG BATAS KHUSUS KENDARAAN (ADAPTIF UNTUK DRONE KETINGGIAN TINGGI)
                if cls_id == 1:
                    min_area = 150 if mode.lower() == "drone" else 500
                    if (box_w * box_h) < min_area:
                        continue # Abaikan noise artefak sangat kecil (< 150 px)

                # FILTER 4: SANITASI KLASIFIKASI BAWAH AIR (ANTI-MISKLASIFIKASI SUBMARINE PADA IKAN)
                if mode.lower() in ["rov", "all"]:
                    cls_id = ThreatEvaluator.sanitize_underwater_target(
                        class_id=cls_id,
                        box_w=box_w,
                        box_h=box_h,
                        frame_w=w,
                        frame_h=h,
                        conf=conf
                    )

                # FILTER 5: SANITASI KLASIFIKASI DRONE (FOLIAGE & BONSAI GUARD ANTI-KENDARAAN)
                if mode.lower() in ["drone", "all"]:
                    crop_box = infer_frame[y1:y2, x1:x2]
                    cls_id = ThreatEvaluator.sanitize_aerial_target(
                        class_id=cls_id,
                        cropped_bgr=crop_box,
                        box_w=box_w,
                        box_h=box_h,
                        conf=conf
                    )

                raw_candidates.append({
                    "class_id": cls_id,
                    "confidence": conf,
                    "box": [int(x1), int(y1), int(x2), int(y2)]
                })

        # TEMPORAL TRACKING & CLASS SMOOTHING (Mencegah Civilian <-> Soldier flickering)
        smoothed_candidates = active_tracker.update(raw_candidates)

        for cand in smoothed_candidates:
            cls_id = cand["class_id"]
            conf = cand["confidence"]
            bx = cand["box"]
            x1, y1, x2, y2 = int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            detected_class_ids.append(cls_id)
            info = ThreatEvaluator.get_info_by_class_id(cls_id)

            display_name = info["display"]
            threat_label = info["threat_label"]
            color_bgr = info["color_bgr"]
            threat_status = info["threat"]

            # PENCATATAN STATISTIK TAKTIS BERDASARKAN KELAS STABIL
            if cls_id == 0:
                drone_stats["soldier"] += 1
            elif cls_id == 1:
                drone_stats["military_vehicle"] += 1
            elif cls_id == 2:
                drone_stats["civilian"] += 1
            elif cls_id == 3:
                drone_stats["tree"] += 1
            elif cls_id == 4:
                rov_stats["submarine"] += 1
            elif cls_id == 5:
                rov_stats["marine_life"] += 1
            elif cls_id == 6:
                rov_stats["coral_reef"] += 1
            elif cls_id == 7:
                rov_stats["diver"] += 1

            if threat_status == "HAZARD":
                hazard_count += 1
            else:
                neutral_count += 1

            det_item = {
                "track_id": cand.get("track_id", 0),
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

        self._draw_detections_on_frame(annotated_frame, detections, show_labels=show_labels)

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

    @classmethod
    def _draw_detections_on_frame(cls, frame: np.ndarray, detections: List[Dict[str, Any]], show_labels: bool = True) -> None:
        """Menggambar daftar bounding box pada frame target secara in-place."""
        is_crowded = len(detections) > 12
        for det in detections:
            box = det.get("bbox") or det.get("box") or [0, 0, 0, 0]
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            color_bgr = tuple(det.get("color_bgr") or ThreatEvaluator.get_info_by_class_id(det.get("class_id", 0))["color_bgr"])
            display_name = det.get("display_name", "")
            conf = float(det.get("confidence", 0.0))
            cls._draw_tactical_bbox(
                frame,
                x1, y1, x2, y2,
                color_bgr,
                display_name,
                conf,
                show_label=show_labels,
                compact_mode=is_crowded
            )

    @classmethod
    def render_overlay(
        cls,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        mode: str = "drone",
        draw_hud_reticle: bool = True,
        show_labels: bool = True,
        enable_clahe: bool = False,
        enable_dusk: bool = False
    ) -> np.ndarray:
        """Menggambar ulang enhancer, HUD reticle, dan cached bounding boxes ke frame terbaru tanpa inference."""
        if enable_clahe and mode.lower() in ["rov", "all"]:
            out_frame = cls.enhance_underwater_frame(frame)
        elif enable_dusk and mode.lower() in ["drone", "all"]:
            out_frame = cls.enhance_dusk_frame(frame)
        else:
            out_frame = frame.copy()

        if draw_hud_reticle:
            cls._draw_tactical_hud_overlay(out_frame, mode)

        if detections:
            cls._draw_detections_on_frame(out_frame, detections, show_labels=show_labels)
        return out_frame

    @staticmethod
    def _draw_tactical_bbox(frame, x1, y1, x2, y2, color, label, conf, show_label=True, compact_mode=False):
        """Menggambar bounding box bergaya Tactical Corner Reticle dengan adaptasi visual terhadap kepadatan."""
        box_w = x2 - x1
        box_h = y2 - y1
        corner_len = int(min(box_w, box_h) * 0.25)
        thickness = 1 if compact_mode else 2

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

        if not show_label:
            return

        if compact_mode:
            # Mode Ringkas: badge mini teks tanpa blok hitam besar agar video tetap jernih
            short_name = label.split("/")[0].strip()
            osd_text = f"{short_name} {int(conf * 100)}%"
            tx = x1 + 2
            ty = max(11, y1 - 3)
            cv2.putText(frame, osd_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, osd_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)
        else:
            # Mode Standar: badge taktis hitam ber-border
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

    @staticmethod
    def enhance_dusk_frame(frame: np.ndarray, gamma: float = 0.65) -> np.ndarray:
        """
        Dusk / Low-Light Aerial Vision Enhancer untuk Drone Mode:
        - Menerapkan Adaptive Gamma Correction untuk mengangkat bayangan gelap sore hari
        - Menerapkan CLAHE pada L-channel (LAB) untuk menonjolkan siluet manusia & tekstur pohon
        - Menajamkan kontur kecil dari ketinggian drone agar confidence manusia meningkat
        """
        if frame is None or frame.size == 0:
            return frame

        try:
            # 1. Gamma Correction (mencerahkan midtones & area remang-remang)
            inv_gamma = 1.0 / max(0.1, gamma)
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype(np.uint8)
            brightened = cv2.LUT(frame, table)

            # 2. CLAHE pada Luminance Channel (LAB)
            lab = cv2.cvtColor(brightened, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            enhanced_lab = cv2.merge((l_enhanced, a, b))
            result = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

            # 3. Subtle Unsharp Masking untuk mempertegas kontur kepala/bahu manusia & dedaunan
            gaussian = cv2.GaussianBlur(result, (0, 0), 2.0)
            sharpened = cv2.addWeighted(result, 1.25, gaussian, -0.25, 0)
            return sharpened
        except Exception:
            return frame
