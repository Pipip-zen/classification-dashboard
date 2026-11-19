"""
Module: core/threat_evaluator.py
Deskripsi:
    Rule Engine Taktis & Klasifikasi Warna Baju (Stage 2):
    - Mode ROV (Danau & Bawah Air: Kapal Selam, Biota, Karang, ROV, Kapal)
    - Mode Drone (POV Umum):
        * Person -> Klasifikasi Warna Baju: Tim A (Baju Biru) vs Tim B (Baju Ungu) vs Sipil (Lainnya)
        * Kendaraan / Vehicle (Kendaraan Umum: Mobil, Truk, dll)
        * Perahu / Kapal (Vessel Danau)
        * Drone FPV
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Set, Optional


class ThreatEvaluator:
    # Taksonomi terpadu 11 kelas (ROV Danau + Drone Aerial Spectator)
    TAXONOMY = {
        0: {
            "name": "soldier",
            "display": "Prajurit / Soldier",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "HAZARD",
            "threat_label": "Kombatan / Target Taktis",
            "color_bgr": (0, 0, 255),      # Merah Taktis (#FF3B30)
            "color_hex": "#FF3B30",
            "ref_width_m": 0.5
        },
        1: {
            "name": "military_vehicle",
            "display": "Kendaraan / Vehicle",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Kendaraan Tempur / Transport",
            "color_bgr": (3, 183, 255),    # Oranye / Amber (#FFB703)
            "color_hex": "#FFB703",
            "ref_width_m": 2.5
        },
        2: {
            "name": "civilian",
            "display": "Warga Sipil / Civilian",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Warga Sipil / Non-Kombatan",
            "color_bgr": (0, 255, 0),      # Hijau Aman (#34C759)
            "color_hex": "#34C759",
            "ref_width_m": 0.5
        },
        3: {
            "name": "ship",
            "display": "Perahu / Kapal Permukaan",
            "domain": "Surface Water",
            "allowed_modes": {"rov", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Wahana Permukaan Air",
            "color_bgr": (0, 165, 255),    # Oranye
            "color_hex": "#FF9500",
            "ref_width_m": 8.0
        },
        4: {
            "name": "submarine",
            "display": "Kapal Selam / Submarine",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "HAZARD",
            "threat_label": "Target Bawah Air (Submarine)",
            "color_bgr": (0, 0, 255),
            "color_hex": "#FF3B30",
            "ref_width_m": 12.0
        },
        5: {
            "name": "marine_life",
            "display": "Ikan / Biota Danau",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Fauna Air / Ikan Danau",
            "color_bgr": (0, 255, 0),
            "color_hex": "#34C759",
            "ref_width_m": 0.4
        },
        6: {
            "name": "coral_reef",
            "display": "Terumbu Karang / Formasi Batuan",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Objek Alami Dasar Danau",
            "color_bgr": (0, 255, 0),
            "color_hex": "#34C759",
            "ref_width_m": 1.5
        },
        7: {
            "name": "rov",
            "display": "Wahana ROV Danau",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "NEUTRAL",
            "threat_label": "ROV Friendly Unit",
            "color_bgr": (255, 255, 0),
            "color_hex": "#00E5FF",
            "ref_width_m": 0.8
        },
        8: {
            "name": "fpv_drone",
            "display": "Drone FPV (Udara)",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Wahana Drone Udara",
            "color_bgr": (0, 255, 102),
            "color_hex": "#00FF66",
            "ref_width_m": 0.4
        },
        9: {
            "name": "tree",
            "display": "Pohon / Vegetasi",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Lanskap / Vegetasi Darat",
            "color_bgr": (34, 139, 34),    # Forest Green
            "color_hex": "#228B22",
            "ref_width_m": 3.0
        },
        10: {
            "name": "building",
            "display": "Bangunan / Struktur",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Struktur / Bangunan Darat",
            "color_bgr": (211, 211, 211),  # Abu-abu Cerah
            "color_hex": "#D3D3D3",
            "ref_width_m": 10.0
        },
        11: {
            "name": "diver",
            "display": "Penyelam / Diver",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Penyelam Bawah Air (Scuba Diver)",
            "color_bgr": (0, 180, 255),    # Biru Langit Cerah (#FFB400 di RGB)
            "color_hex": "#00B4FF",
            "ref_width_m": 0.6
        }
    }

    ROV_ALLOWED_CLASSES: Set[int] = {3, 4, 5, 6, 7, 11}
    DRONE_ALLOWED_CLASSES: Set[int] = {0, 1, 2, 8, 9, 10}

    @classmethod
    def sanitize_underwater_target(
        cls,
        class_id: int,
        box_w: int,
        box_h: int,
        frame_w: int,
        frame_h: int,
        conf: float
    ) -> int:
        """
        Anti-Misclassification Engine Bawah Air:
        Mencegah ikan laut atau biota kecil disalahartikan sebagai Kapal Selam (Submarine).
        Kapal Selam taktis adalah wahana militer masif dengan rasio panjang/tinggi tinggi
        dan footprint visual signifikan (>6% luasan frame atau lebar > 30% layar).
        Jika objek terdeteksi sebagai submarine namun ukurannya kecil atau proporsinya seperti ikan,
        maka otomatis direklasifikasi secara cerdas ke kelas 5 (marine_life).
        """
        if class_id == 4: # submarine
            total_frame_area = max(1, frame_w * frame_h)
            box_area = box_w * box_h
            area_ratio = box_area / total_frame_area
            aspect_ratio = max(box_w, box_h) / max(1, min(box_w, box_h))

            # Jika luas bounding box < 6% layar atau lebar box < 25% lebar frame, atau conf < 0.85
            # maka objek tersebut adalah fauna laut (ikan), BUKAN kapal selam militer!
            if area_ratio < 0.06 or (box_w < frame_w * 0.25 and box_h < frame_h * 0.25):
                return 5 # Remap ke marine_life
            if aspect_ratio < 2.0 and conf < 0.85:
                return 5 # Remap ke marine_life

        return class_id

    @classmethod
    def sanitize_aerial_target(
        cls,
        class_id: int,
        cropped_bgr: Optional[np.ndarray],
        box_w: int,
        box_h: int,
        conf: float
    ) -> int:
        """
        Anti-Misclassification Engine Mode Drone (Foliage & Tree Guard):
        Hanya aktif jika AI ragu-ragu (conf < 0.45) dan area INTI tengah (center crop)
        didominasi dedaunan organik (> 50% green foliage ratio).
        Mencegah helikopter, mobil, dan bangunan yang berada di dekat rumput
        salah di-remap menjadi pohon.
        """
        # Jangan pernah ubah jika model sudah yakin (conf >= 0.45) atau bukan kendaraan
        if class_id != 1 or conf >= 0.45:
            return class_id

        if cropped_bgr is not None and cropped_bgr.shape[0] > 10 and cropped_bgr.shape[1] > 10:
            try:
                ch, cw = cropped_bgr.shape[:2]
                # Ambil 50% bagian tengah saja (center crop) agar rumput di sekeliling tidak terhitung
                y_start, y_end = int(ch * 0.25), int(ch * 0.75)
                x_start, x_end = int(cw * 0.25), int(cw * 0.75)
                core_crop = cropped_bgr[y_start:y_end, x_start:x_end]
                
                if core_crop.size < 20:
                    return class_id

                # 1. Analisis Klorofil via Color Space (Excess Green Index & HSV)
                b, g, r = cv2.split(core_crop.astype(np.float32))
                exg = (2.0 * g) - r - b
                green_foliage_ratio = np.count_nonzero(exg > 5.0) / float(core_crop.shape[0] * core_crop.shape[1])

                hsv = cv2.cvtColor(core_crop, cv2.COLOR_BGR2HSV)
                lower_foliage = np.array([25, 30, 30])
                upper_foliage = np.array([85, 255, 255])
                foliage_mask = cv2.inRange(hsv, lower_foliage, upper_foliage)
                hsv_foliage_ratio = np.count_nonzero(foliage_mask) / float(core_crop.shape[0] * core_crop.shape[1])

                # 2. Analisis Tekstur Organik Dedaunan (Laplacian Variance)
                gray = cv2.cvtColor(core_crop, cv2.COLOR_BGR2GRAY)
                lap_var = cv2.Laplacian(gray, cv2.CV_32F).var()

                # Hanya remap jika inti objek didominasi daun (>50%) dan bertekstur organik acak (lap_var > 50)
                if (green_foliage_ratio > 0.50 or hsv_foliage_ratio > 0.55) and lap_var > 50.0:
                    return 9 # Remap ke tree (Pohon / Vegetasi)
            except Exception:
                pass
        return class_id

    @classmethod
    def is_class_allowed_for_mode(cls, class_id: int, mode: str) -> bool:
        mode_lower = mode.lower()
        if mode_lower == "all":
            return True
        elif mode_lower == "rov":
            return class_id in cls.ROV_ALLOWED_CLASSES
        elif mode_lower == "drone":
            return class_id in cls.DRONE_ALLOWED_CLASSES
        return True

    @classmethod
    def get_info_by_class_id(cls, class_id: int) -> Dict[str, Any]:
        return cls.TAXONOMY.get(
            class_id,
            {
                "name": f"target_{class_id}",
                "display": f"Target ({class_id})",
                "domain": "Unknown",
                "allowed_modes": {"all"},
                "threat": "UNKNOWN",
                "threat_label": "Tidak Terdefinisi",
                "color_bgr": (255, 255, 0),
                "color_hex": "#FFCC00",
                "ref_width_m": 1.0
            }
        )

    @classmethod
    def classify_soldier_team(cls, cropped_bgr: np.ndarray) -> Tuple[str, str, Tuple[int, int, int], str]:
        """
        Stage 2: Pembedaan Tim A vs Tim B Berdasarkan Warna Baju (Torso Upper Body):
        - Baju BIRU  -> Tim A (Box Biru: #0099FF / BGR (255, 153, 0))
        - Baju UNGU  -> Tim B (Box Ungu: #9D4EDD / BGR (221, 78, 157))
        - Warna Lain -> Warga Sipil / Netral (Box Hijau: #34C759 / BGR (0, 255, 0))
        """
        if cropped_bgr is None or cropped_bgr.size == 0:
            return ("Sipil / Netral", "Bukan Anggota Tim A/B", (0, 255, 0), "#34C759")

        h, w = cropped_bgr.shape[:2]

        # Isolasi area dada/baju (Torso: 25% s/d 75% tinggi tubuh, memotong rambut & celana)
        y_start = int(h * 0.25)
        y_end = int(h * 0.75)
        if (y_end - y_start) > 5:
            torso_bgr = cropped_bgr[y_start:y_end, :]
        else:
            torso_bgr = cropped_bgr

        hsv = cv2.cvtColor(torso_bgr, cv2.COLOR_BGR2HSV)
        total_pixels = float(torso_bgr.shape[0] * torso_bgr.shape[1])

        # 1. Masking Spektrum Warna BIRU (Tim A)
        # Rentang Hue Biru: 95 s/d 130
        lower_blue = np.array([95, 35, 35])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        blue_ratio = np.count_nonzero(blue_mask) / total_pixels

        # 2. Masking Spektrum Warna UNGU / VIOLET (Tim B)
        # Rentang Hue Ungu: 130 s/d 165
        lower_purple = np.array([130, 35, 35])
        upper_purple = np.array([165, 255, 255])
        purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)
        purple_ratio = np.count_nonzero(purple_mask) / total_pixels

        # Ambang batas persentase warna baju minimal
        SHIRT_COLOR_THRESHOLD = 0.06

        if blue_ratio >= SHIRT_COLOR_THRESHOLD and blue_ratio >= purple_ratio:
            return ("Person [TIM A - BIRU]", "Anggota Tim A (Baju Biru)", (255, 153, 0), "#0099FF")
        elif purple_ratio >= SHIRT_COLOR_THRESHOLD and purple_ratio > blue_ratio:
            return ("Person [TIM B - UNGU]", "Anggota Tim B (Baju Ungu)", (221, 78, 157), "#9D4EDD")
        else:
            # Tidak mengenakan baju biru maupun ungu -> Warga Sipil / Netral
            return ("Warga Sipil / Netral", "Pakaian Biasa (Bukan Tim A/B)", (0, 255, 0), "#34C759")

    @classmethod
    def determine_environment(cls, detected_class_ids: List[int], mode: str = "all") -> Tuple[str, str]:
        if mode.lower() == "rov":
            return ("Lake / Underwater Ops", "Bawah Air & Danau")
        elif mode.lower() == "drone":
            return ("Aerial Spectator / Drone POV", "Ruang Udara & Lapangan")

        if not detected_class_ids:
            return ("Scanning Horizon", "Standby")

        domain_counts = {"Land": 0, "Surface Water": 0, "Underwater": 0}
        for cid in detected_class_ids:
            info = cls.get_info_by_class_id(cid)
            domain = info.get("domain")
            if domain in domain_counts:
                domain_counts[domain] += 1

        top_domain = max(domain_counts, key=domain_counts.get)
        return (top_domain, f"{domain_counts[top_domain]} target")
