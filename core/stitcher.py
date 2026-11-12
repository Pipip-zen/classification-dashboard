"""
Module: core/stitcher.py
Deskripsi:
    Modul Image Stitching untuk menggabungkan serangkaian citra foto beririsan
    dari jalur patroli kamera ROV bawah air atau Drone udara menjadi citra panorama.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional


class ImageStitcher:
    def __init__(self, mode: str = "panorama"):
        self.mode = mode

    def stitch_images(
        self,
        images: List[np.ndarray],
        crop_black_borders: bool = True
    ) -> Tuple[bool, Optional[np.ndarray], str]:
        if len(images) < 2:
            return False, None, "Dibutuhkan minimal 2 gambar beririsan untuk proses stitching."

        stitcher_mode = (
            cv2.Stitcher_SCANS if self.mode == "scans" else cv2.Stitcher_PANORAMA
        )
        stitcher = cv2.Stitcher_create(stitcher_mode)

        status, panorama = stitcher.stitch(images)

        if status == cv2.Stitcher_OK:
            if crop_black_borders:
                panorama = self._trim_black_borders(panorama)
            return True, panorama, "Stitching berhasil diselesaikan dengan baik."
        elif status == cv2.Stitcher_ERR_NEED_MORE_IMGS:
            return False, None, "Gagal: Kurang titik fitur yang beririsan (overlap) antar foto. Pastikan overlap > 30%."
        elif status == cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL:
            return False, None, "Gagal: Estimasi matriks homografi gagal. Pastikan foto diambil dari orientasi searah."
        elif status == cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL:
            return False, None, "Gagal: Penyesuaian parameter kalibrasi kamera gagal."
        else:
            return False, None, f"Gagal melakukan stitching (Kode Error: {status})."

    @staticmethod
    def _trim_black_borders(image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return image

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        if w > 10 and h > 10:
            return image[y:y+h, x:x+w]
        return image
