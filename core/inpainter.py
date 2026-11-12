"""
Module: core/inpainter.py
Deskripsi:
    Modul Image Inpainting untuk membersihkan noise visual, artefak kamera,
    atau menyensor koordinat sensitif/OSD (On-Screen Display) sebelum laporan dibagikan.
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional


class ImageInpainter:
    def __init__(self, method: str = "telea", radius: int = 3):
        self.method = method
        self.radius = max(1, radius)

    def inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        method: Optional[str] = None,
        radius: Optional[int] = None
    ) -> np.ndarray:
        selected_method = method or self.method
        selected_radius = radius or self.radius

        flags = cv2.INPAINT_TELEA if selected_method.lower() == "telea" else cv2.INPAINT_NS

        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

        _, binary_mask = cv2.threshold(mask, 10, 255, cv2.THRESH_BINARY)
        result = cv2.inpaint(image, binary_mask, inpaintRadius=selected_radius, flags=flags)
        return result

    @staticmethod
    def create_box_mask(
        image_shape: Tuple[int, int, ...],
        boxes: List[Tuple[int, int, int, int]]
    ) -> np.ndarray:
        h, w = image_shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        for (x1, y1, x2, y2) in boxes:
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

        return mask
