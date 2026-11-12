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
from typing import Dict, Any, List, Tuple, Set


class ThreatEvaluator:
    # Taksonomi terpadu 9 kelas
    TAXONOMY = {
        0: {
            "name": "soldier",
            "display": "Orang / Person",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "HAZARD",
            "threat_label": "Personel (Akan dievaluasi warna baju)",
            "color_bgr": (255, 153, 0),    # Default Biru/Cyan
            "color_hex": "#0099FF",
            "ref_width_m": 0.5
        },
        1: {
            "name": "military_vehicle",
            "display": "Kendaraan / Vehicle",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Kendaraan Umum (Mobil/Truk/Darat)",
            "color_bgr": (3, 183, 255),    # Oranye / Amber Umum
            "color_hex": "#FFB703",
            "ref_width_m": 2.5
        },
        2: {
            "name": "civilian",
            "display": "Orang / Person",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Sipil / Non-Tim",
            "color_bgr": (0, 255, 0),      # Hijau
            "color_hex": "#34C759",
            "ref_width_m": 0.5
        },
        3: {
            "name": "ship",
            "display": "Perahu / Kapal Danau",
            "domain": "Surface Water",
            "allowed_modes": {"rov", "drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Wahana Permukaan Danau",
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
        }
    }

    ROV_ALLOWED_CLASSES: Set[int] = {3, 4, 5, 6, 7}
    DRONE_ALLOWED_CLASSES: Set[int] = {0, 1, 2, 3, 8}

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
