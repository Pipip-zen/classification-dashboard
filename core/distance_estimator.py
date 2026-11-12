"""
Module: core/distance_estimator.py
Deskripsi:
    Menghitung estimasi jarak objek ke sensor kamera menggunakan
    Model Geometri Kamera Pinhole: D = (W_real * f) / W_pixel.
"""

from typing import Optional
from core.threat_evaluator import ThreatEvaluator


class DistanceEstimator:
    CAMERA_PROFILES = {
        "fpv_drone_wide": {
            "name": "Drone FPV (Wide Angle FOV 110-120°)",
            "focal_length_px": 650.0
        },
        "drone_standard": {
            "name": "Drone Surveillance Standard (FOV 80°)",
            "focal_length_px": 850.0
        },
        "rov_underwater_flat": {
            "name": "ROV Underwater Camera (Flat Port)",
            "focal_length_px": 900.0
        },
        "rov_underwater_dome": {
            "name": "ROV Underwater Camera (Dome Port)",
            "focal_length_px": 720.0
        },
        "webcam_default": {
            "name": "Standard Laptop / USB Webcam",
            "focal_length_px": 800.0
        }
    }

    def __init__(self, focal_length_px: float = 800.0):
        self.focal_length_px = focal_length_px

    def set_camera_profile(self, profile_key: str):
        if profile_key in self.CAMERA_PROFILES:
            self.focal_length_px = self.CAMERA_PROFILES[profile_key]["focal_length_px"]

    def set_custom_focal_length(self, focal_length_px: float):
        if focal_length_px > 0:
            self.focal_length_px = focal_length_px

    def estimate_distance(
        self,
        pixel_width: float,
        class_id: Optional[int] = None,
        class_name: Optional[str] = None,
        custom_real_width_m: Optional[float] = None
    ) -> Optional[float]:
        if pixel_width <= 1.0:
            return None

        if custom_real_width_m is not None and custom_real_width_m > 0:
            real_width = custom_real_width_m
        elif class_id is not None:
            info = ThreatEvaluator.get_info_by_class_id(class_id)
            real_width = info.get("ref_width_m", 1.0)
        elif class_name is not None:
            info = ThreatEvaluator.get_info_by_name(class_name)
            real_width = info.get("ref_width_m", 1.0)
        else:
            real_width = 1.0

        distance_m = (real_width * self.focal_length_px) / pixel_width
        return round(float(distance_m), 2)
