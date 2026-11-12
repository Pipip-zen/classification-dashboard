"""
Module: core/threat_evaluator.py
Deskripsi:
    Rule Engine untuk mengevaluasi status ancaman (Threat Status: HAZARD vs NEUTRAL),
    pemisahan operasional wahana (Mode ROV Danau/Games vs Mode Drone Spectator/Recon),
    dan klasifikasi prajurit Tim A vs Tim B (Stage 2).
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Set


class ThreatEvaluator:
    # Taksonomi terpadu 9 kelas
    TAXONOMY = {
        0: {
            "name": "soldier",
            "display": "Prajurit (Soldier)",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "HAZARD",
            "threat_label": "Berbahaya (Ancaman Personel)",
            "color_bgr": (0, 0, 255),      # Merah
            "color_hex": "#FF3B30",
            "ref_width_m": 0.5
        },
        1: {
            "name": "military_vehicle",
            "display": "Kendaraan Tempur (Tank/IFV)",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "HAZARD",
            "threat_label": "Berbahaya (Lapis Baja Musuh)",
            "color_bgr": (0, 0, 255),
            "color_hex": "#FF3B30",
            "ref_width_m": 3.2
        },
        2: {
            "name": "civilian",
            "display": "Sipil (Civilian / Netral)",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Aman (Warga Sipil / Non-Kombatan)",
            "color_bgr": (0, 255, 0),      # Hijau
            "color_hex": "#34C759",
            "ref_width_m": 0.5
        },
        3: {
            "name": "ship",
            "display": "Kapal / Perahu Danau",
            "domain": "Surface Water",
            "allowed_modes": {"rov", "drone", "all"},
            "threat": "HAZARD",
            "threat_label": "Waspada (Vessel Permukaan Air)",
            "color_bgr": (0, 165, 255),    # Oranye Waspada
            "color_hex": "#FF9500",
            "ref_width_m": 15.0
        },
        4: {
            "name": "submarine",
            "display": "Kapal Selam (Submarine)",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "HAZARD",
            "threat_label": "Berbahaya (Wahana Bawah Air)",
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
            "threat_label": "Netral (Fauna Air / Danau)",
            "color_bgr": (0, 255, 0),
            "color_hex": "#34C759",
            "ref_width_m": 0.4
        },
        6: {
            "name": "coral_reef",
            "display": "Terumbu Karang / Batuan",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Netral (Formasi Alam Danau)",
            "color_bgr": (0, 255, 0),
            "color_hex": "#34C759",
            "ref_width_m": 1.5
        },
        7: {
            "name": "rov",
            "display": "Wahana ROV (Friendly)",
            "domain": "Underwater",
            "allowed_modes": {"rov", "all"},
            "threat": "NEUTRAL",
            "threat_label": "Kawan (ROV Patroli / Games)",
            "color_bgr": (255, 255, 0),    # Cyan/Kuning
            "color_hex": "#00E5FF",
            "ref_width_m": 0.8
        },
        8: {
            "name": "fpv_drone",
            "display": "Drone FPV (Friendly/Spectator)",
            "domain": "Land",
            "allowed_modes": {"drone", "all"},
            "threat": "HAZARD",
            "threat_label": "Waspada (Wahana Udara)",
            "color_bgr": (0, 165, 255),
            "color_hex": "#FF9500",
            "ref_width_m": 0.4
        }
    }

    # Pembagian Filter Kelas Berdasarkan Mode Operasi
    ROV_ALLOWED_CLASSES: Set[int] = {3, 4, 5, 6, 7}     # Kapal, Kapal Selam, Biota, Karang/Batuan, ROV
    DRONE_ALLOWED_CLASSES: Set[int] = {0, 1, 2, 3, 8}   # Soldier, Kendaraan, Sipil, Kapal/Perahu dari atas, Drone

    @classmethod
    def is_class_allowed_for_mode(cls, class_id: int, mode: str) -> bool:
        """Memeriksa apakah kelas target relevan untuk wahana yang sedang aktif."""
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
        Stage 2: Spectator Affiliation Classifier
        - Seragam Hijau Camo = Tim A (Merah)
        - Seragam Tan / Hitam = Tim B (Ungu / Biru Taktis)
        """
        if cropped_bgr is None or cropped_bgr.size == 0:
            return ("Soldier (Tim A)", "Berbahaya (Prajurit Tim A)", (0, 0, 255), "#FF3B30")

        hsv = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        green_ratio = np.count_nonzero(green_mask) / float(cropped_bgr.shape[0] * cropped_bgr.shape[1])

        lower_tan = np.array([10, 30, 60])
        upper_tan = np.array([25, 200, 200])
        tan_mask = cv2.inRange(hsv, lower_tan, upper_tan)
        tan_ratio = np.count_nonzero(tan_mask) / float(cropped_bgr.shape[0] * cropped_bgr.shape[1])

        if green_ratio >= tan_ratio and green_ratio > 0.08:
            return ("Soldier [TIM A]", "Target Tempur: Tim A (Camo Hijau)", (0, 0, 255), "#FF3B30")
        else:
            return ("Soldier [TIM B]", "Target Tempur: Tim B (Desert/Hitam)", (255, 0, 128), "#AF52DE")

    @classmethod
    def determine_environment(cls, detected_class_ids: List[int], mode: str = "all") -> Tuple[str, str]:
        if mode.lower() == "rov":
            return ("Lake / Underwater Ops", "Bawah Air & Danau")
        elif mode.lower() == "drone":
            return ("Aerial Recon / Spectator", "Ruang Udara & Darat")

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
