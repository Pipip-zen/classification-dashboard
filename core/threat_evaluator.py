"""
Module: core/threat_evaluator.py
Deskripsi:
    Rule Engine untuk mengevaluasi status ancaman (Threat Status: HAZARD vs NEUTRAL),
    kode warna taktis, dan identifikasi domain lingkungan (Land / Surface / Underwater).
    Mendukung Stage 2 Color/Camo Classifier untuk membedakan Soldier Tim A vs Tim B.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple


class ThreatEvaluator:
    # Taksonomi terpadu 9 kelas sesuai data/unified_dataset/data.yaml
    TAXONOMY = {
        0: {
            "name": "soldier",
            "display": "Prajurit (Soldier)",
            "domain": "Land",
            "threat": "HAZARD",
            "threat_label": "Berbahaya (Ancaman Personel Militer)",
            "color_bgr": (0, 0, 255),      # Merah
            "color_hex": "#FF3B30",
            "ref_width_m": 0.5             # Lebar pundak rata-rata
        },
        1: {
            "name": "military_vehicle",
            "display": "Kendaraan Tempur (Tank/IFV)",
            "domain": "Land",
            "threat": "HAZARD",
            "threat_label": "Berbahaya (Kendaraan Lapis Baja Musuh)",
            "color_bgr": (0, 0, 255),
            "color_hex": "#FF3B30",
            "ref_width_m": 3.2
        },
        2: {
            "name": "civilian",
            "display": "Sipil (Civilian / Non-Militer)",
            "domain": "Land",
            "threat": "NEUTRAL",
            "threat_label": "Tidak Berbahaya (Objek/Warga Sipil)",
            "color_bgr": (0, 255, 0),      # Hijau
            "color_hex": "#34C759",
            "ref_width_m": 0.5
        },
        3: {
            "name": "ship",
            "display": "Kapal Laut (Vessel/Ship)",
            "domain": "Surface Water",
            "threat": "HAZARD",
            "threat_label": "Perhatian (Kapal Permukaan Air)",
            "color_bgr": (0, 165, 255),    # Oranye / Waspada
            "color_hex": "#FF9500",
            "ref_width_m": 25.0
        },
        4: {
            "name": "submarine",
            "display": "Kapal Selam (Submarine)",
            "domain": "Underwater",
            "threat": "HAZARD",
            "threat_label": "Berbahaya (Armada Bawah Air Musuh)",
            "color_bgr": (0, 0, 255),
            "color_hex": "#FF3B30",
            "ref_width_m": 12.0
        },
        5: {
            "name": "marine_life",
            "display": "Ikan / Biota Laut",
            "domain": "Underwater",
            "threat": "NEUTRAL",
            "threat_label": "Tidak Berbahaya (Biota Air Alami)",
            "color_bgr": (0, 255, 0),
            "color_hex": "#34C759",
            "ref_width_m": 0.4
        },
        6: {
            "name": "coral_reef",
            "display": "Terumbu Karang / Tanaman Air",
            "domain": "Underwater",
            "threat": "NEUTRAL",
            "threat_label": "Tidak Berbahaya (Formasi Alam)",
            "color_bgr": (0, 255, 0),
            "color_hex": "#34C759",
            "ref_width_m": 1.5
        },
        7: {
            "name": "rov",
            "display": "ROV (Drone Bawah Air)",
            "domain": "Underwater",
            "threat": "NEUTRAL",
            "threat_label": "Wahana Patroli Bawah Air (Friendly)",
            "color_bgr": (255, 255, 0),    # Cyan/Kuning
            "color_hex": "#00C7BE",
            "ref_width_m": 0.8
        },
        8: {
            "name": "fpv_drone",
            "display": "Drone FPV (Wahana Udara)",
            "domain": "Land",
            "threat": "HAZARD",
            "threat_label": "Waspada (Drone Udara Terdeteksi)",
            "color_bgr": (0, 165, 255),
            "color_hex": "#FF9500",
            "ref_width_m": 0.4
        }
    }

    @classmethod
    def get_info_by_class_id(cls, class_id: int) -> Dict[str, Any]:
        """Mengambil metadata kelas berdasarkan ID numerik."""
        return cls.TAXONOMY.get(
            class_id,
            {
                "name": f"target_{class_id}",
                "display": f"Target ({class_id})",
                "domain": "Unknown",
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
        Stage 2: Affiliation Classifier.
        Menganalisis proporsi ruang warna HSV pada bounding box prajurit:
        - Hijau dominan (Camo Hutan / TNI) -> Soldier Tim A (Merah)
        - Gurun/Hitam/Navy dominan        -> Soldier Tim B (Biru/Merah Muda)
        Returns: (team_name, threat_label, color_bgr, color_hex)
        """
        if cropped_bgr is None or cropped_bgr.size == 0:
            return ("Soldier (Tim A)", "Berbahaya (Prajurit Tim A)", (0, 0, 255), "#FF3B30")

        # Konversi ke ruang warna HSV
        hsv = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Masking warna hijau (Woodland Camouflage - Tim A)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        green_ratio = np.count_nonzero(green_mask) / float(cropped_bgr.shape[0] * cropped_bgr.shape[1])

        # Masking warna cokelat gurun / tan (Desert Camo - Tim B)
        lower_tan = np.array([10, 30, 60])
        upper_tan = np.array([25, 200, 200])
        tan_mask = cv2.inRange(hsv, lower_tan, upper_tan)
        tan_ratio = np.count_nonzero(tan_mask) / float(cropped_bgr.shape[0] * cropped_bgr.shape[1])

        if green_ratio >= tan_ratio and green_ratio > 0.08:
            return ("Soldier (Tim A - Camo Hijau)", "Berbahaya (Prajurit Tim A)", (0, 0, 255), "#FF3B30")
        else:
            return ("Soldier (Tim B - Desert/Hitam)", "Berbahaya (Prajurit Tim B)", (255, 0, 128), "#AF52DE")

    @classmethod
    def determine_environment(cls, detected_class_ids: List[int]) -> Tuple[str, str]:
        """
        Menentukan domain lingkungan utama dari kumpulan objek yang terdeteksi.
        Returns: (domain_name, confidence_level)
        """
        if not detected_class_ids:
            return ("Unknown / Scanning", "Idle")

        domain_counts = {"Land": 0, "Surface Water": 0, "Underwater": 0}
        for cid in detected_class_ids:
            info = cls.get_info_by_class_id(cid)
            domain = info.get("domain")
            if domain in domain_counts:
                domain_counts[domain] += 1

        top_domain = max(domain_counts, key=domain_counts.get)
        if domain_counts[top_domain] == 0:
            return ("Unknown / Scanning", "Idle")

        return (top_domain, f"{domain_counts[top_domain]}/{len(detected_class_ids)} target")

