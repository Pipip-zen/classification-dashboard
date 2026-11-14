"""
Module: core/stream_capture.py
Deskripsi:
    Penanganan berbagai jenis stream input:
    1. Screen Mirroring / Desktop Window Capture (untuk view ROV/Drone software)
    2. Network Stream UDP / RTSP (Protokol video stream bawaan ROV & Drone)
    3. Direct USB Camera / Webcam
    4. Virtual Video Testbench (looping offline video untuk pengujian mingguan)
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
        """Membuka koneksi direct camera USB / webcam."""
        self.release()
        self.cap = cv2.VideoCapture(camera_index)
        return self.cap.isOpened()

    def open_network_stream(self, stream_url: str) -> bool:
        """
        Membuka network video stream (UDP / RTSP / HTTP).
        Mendukung protokol UDP bawaan ROV (misal: udp://@:5600, udp://192.168.2.1:5600, udp://127.0.0.1:5600).
        """
        self.release()
        clean_url = stream_url.strip()

        # Tuning khusus stream UDP H.264 ROV agar low-latency dan anti-packet drop
        if clean_url.startswith("udp://"):
            # Jika belum ada parameter buffer di URL, tambahkan buffer & overrun tuning
            if "?" not in clean_url:
                tuned_url = f"{clean_url}?overrun_nonfatal=1&fifo_size=50000000"
            else:
                tuned_url = clean_url

            # Coba backend FFMPEG
            self.cap = cv2.VideoCapture(tuned_url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                return True

        # Fallback coba buka direct URL
        self.cap = cv2.VideoCapture(clean_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(clean_url)

        return self.cap.isOpened()

    def open_video_file(self, video_path: str) -> bool:
        """Membuka file video lokal (MP4/AVI)."""
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
