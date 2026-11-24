"""
Module: core/orientation_estimator.py
Deskripsi:
    Estimator orientasi wahana (Yaw / Compass Heading) berbasis Computer Vision murni:
    - Algoritma: Lucas-Kanade Sparse Optical Flow (cv2.calcOpticalFlowPyrLK)
    - Fitur Ekstraksi: Shi-Tomasi Corner Detector (cv2.goodFeaturesToTrack)
    - ROI: Area horizon tengah-atas frame (10% - 75% tinggi) untuk meminimalkan paralaks darat
    - Mengonversi pergeseran horizontal median piksel menjadi rotasi sudut yaw (derajat)
    - Menyediakan antarmuka kalibrasi manual (Set North & Heading Offset)
"""

import time
from typing import Dict, Any, Optional
import cv2
import numpy as np


class OrientationEstimator:
    CARDINALS = [
        (337.5, 360.0, "N"),
        (0.0, 22.5, "N"),
        (22.5, 67.5, "NE"),
        (67.5, 112.5, "E"),
        (112.5, 157.5, "SE"),
        (157.5, 202.5, "S"),
        (202.5, 247.5, "SW"),
        (247.5, 292.5, "W"),
        (292.5, 337.5, "NW"),
    ]

    def __init__(
        self,
        hfov_deg: float = 85.0,
        min_tracked_points: int = 25,
        max_corners: int = 120,
        noise_deadband_px: float = 0.25
    ):
        self.hfov_deg = float(hfov_deg)
        self.min_tracked_points = int(min_tracked_points)
        self.max_corners = int(max_corners)
        self.noise_deadband_px = float(noise_deadband_px)

        self.current_heading_deg: float = 0.0
        self.prev_gray: Optional[np.ndarray] = None
        self.prev_pts: Optional[np.ndarray] = None
        self.last_timestamp: float = time.time()
        self.turn_rate_dps: float = 0.0
        self.is_calibrated: bool = False

        # Parameter Lucas-Kanade
        self.lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 15, 0.03)
        )

        # Parameter Shi-Tomasi
        self.feature_params = dict(
            maxCorners=self.max_corners,
            qualityLevel=0.015,
            minDistance=14,
            blockSize=7
        )

    def set_north(self) -> float:
        """Me-reset acuan utara seketika ke 000.0 derajat."""
        self.current_heading_deg = 0.0
        self.is_calibrated = True
        return self.current_heading_deg

    def set_heading(self, deg: float) -> float:
        """Mengatur nilai derajat heading saat ini secara manual."""
        self.current_heading_deg = float(deg % 360.0)
        self.is_calibrated = True
        return self.current_heading_deg

    def reset(self) -> None:
        """Mereset riwayat tracking saat pergantian stream atau video."""
        self.prev_gray = None
        self.prev_pts = None
        self.last_timestamp = time.time()
        self.turn_rate_dps = 0.0

    @classmethod
    def deg_to_cardinal(cls, deg: float) -> str:
        d = deg % 360.0
        for low, high, card in cls.CARDINALS:
            if low <= d < high:
                return card
        return "N"

    def _extract_horizon_features(self, gray: np.ndarray) -> Optional[np.ndarray]:
        h, w = gray.shape[:2]
        # Mask horizon tengah-atas (12% s/d 70% tinggi frame)
        mask = np.zeros_like(gray)
        y1, y2 = int(h * 0.12), int(h * 0.70)
        mask[y1:y2, :] = 255
        pts = cv2.goodFeaturesToTrack(gray, mask=mask, **self.feature_params)
        return pts

    def update(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Menghitung pergeseran yaw kamera dari frame ke frame.
        Mengembalikan kamus data telemetri kompas.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return {
                "heading_deg": round(self.current_heading_deg, 1),
                "cardinal": self.deg_to_cardinal(self.current_heading_deg),
                "turn_rate_dps": 0.0,
                "tracked_points": 0,
                "is_calibrated": self.is_calibrated
            }

        now = time.time()
        dt = max(1e-4, now - self.last_timestamp)
        self.last_timestamp = now

        curr_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = curr_gray.shape[:2]

        tracked_count = 0

        # Jika belum ada frame sebelumnya atau titik pelacakan kurang dari ambang batas
        if self.prev_gray is None or self.prev_pts is None or len(self.prev_pts) < self.min_tracked_points:
            self.prev_gray = curr_gray
            self.prev_pts = self._extract_horizon_features(curr_gray)
            tracked_count = len(self.prev_pts) if self.prev_pts is not None else 0
            return {
                "heading_deg": round(self.current_heading_deg, 1),
                "cardinal": self.deg_to_cardinal(self.current_heading_deg),
                "turn_rate_dps": round(self.turn_rate_dps, 1),
                "tracked_points": tracked_count,
                "is_calibrated": self.is_calibrated
            }

        # Hitung Optical Flow piramida Lucas-Kanade
        p1, st, err = cv2.calcOpticalFlowPyrLK(
            self.prev_gray,
            curr_gray,
            self.prev_pts,
            None,
            **self.lk_params
        )

        delta_yaw_deg = 0.0

        if p1 is not None and st is not None:
            good_curr = p1[st == 1]
            good_prev = self.prev_pts[st == 1]
            tracked_count = len(good_curr)

            if tracked_count >= 8:
                # Pergeseran horizontal piksel (dx = x_curr - x_prev)
                # Jika kamera putar kanan (yaw right), latar belakang bergeser ke kiri (dx < 0).
                # Rotasi yaw adalah -dx.
                dx_list = good_curr[:, 0] - good_prev[:, 0]
                median_dx = float(np.median(dx_list))

                # Filter deadband noise kecil getaran kamera
                if abs(median_dx) > self.noise_deadband_px:
                    # Konversi piksel ke derajat sudut
                    delta_yaw_deg = - (median_dx / float(w)) * self.hfov_deg
                    self.current_heading_deg = (self.current_heading_deg + delta_yaw_deg) % 360.0
                    self.turn_rate_dps = delta_yaw_deg / dt
                else:
                    self.turn_rate_dps = 0.0

                # Perbarui titik pelacak aktif
                self.prev_pts = good_curr.reshape(-1, 1, 2)
            else:
                self.prev_pts = None
                self.turn_rate_dps = 0.0
        else:
            self.prev_pts = None
            self.turn_rate_dps = 0.0

        # Refresh deteksi fitur jika titik mulai menipis
        if self.prev_pts is None or len(self.prev_pts) < self.min_tracked_points:
            self.prev_pts = self._extract_horizon_features(curr_gray)

        self.prev_gray = curr_gray

        return {
            "heading_deg": round(self.current_heading_deg, 1),
            "cardinal": self.deg_to_cardinal(self.current_heading_deg),
            "turn_rate_dps": round(self.turn_rate_dps, 1),
            "tracked_points": tracked_count,
            "is_calibrated": self.is_calibrated
        }
