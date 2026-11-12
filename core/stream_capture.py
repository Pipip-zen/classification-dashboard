"""
Module: core/stream_capture.py
Deskripsi:
    Penanganan berbagai jenis stream input:
    1. Screen Mirroring / Desktop Window Capture (untuk view ROV/Drone software)
    2. Direct Camera / Webcam / RTSP
    3. Virtual Video Testbench (looping offline video untuk pengujian mingguan)
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Any

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class StreamCapture:
    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.sct: Optional[Any] = None
        if MSS_AVAILABLE:
            self.sct = mss.mss()

    def open_camera(self, camera_index: int = 0) -> bool:
        self.release()
        self.cap = cv2.VideoCapture(camera_index)
        return self.cap.isOpened()

    def open_video_file(self, video_path: str) -> bool:
        self.release()
        self.cap = cv2.VideoCapture(video_path)
        return self.cap.isOpened()

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.cap is None or not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        return ret, frame

    def read_virtual_loop_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.cap is None or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        return ret, frame

    def capture_screen_region(
        self,
        top: int = 100,
        left: int = 100,
        width: int = 1280,
        height: int = 720
    ) -> Optional[np.ndarray]:
        if not MSS_AVAILABLE or self.sct is None:
            return None

        monitor = {"top": top, "left": left, "width": width, "height": height}
        sct_img = self.sct.grab(monitor)
        frame = np.array(sct_img)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

