"""
Module: core/stream_capture.py
Deskripsi:
    Penanganan berbagai jenis stream input:
    1. Screen Mirroring / Desktop Window Capture (untuk view ROV/Drone software)
    2. Network Stream UDP / RTSP / SDP (Protokol video stream bawaan ROV & Drone)
       - Mendukung file .sdp yang di-download dari BlueOS Camera Manager
       - Mendukung RTSP dari BlueOS (digunakan oleh Cockpit via WebRTC proxy)
       - Mendukung raw UDP dengan auto-tuning FFMPEG
    3. Direct USB Camera / Webcam
    4. Virtual Video Testbench (looping offline video untuk pengujian mingguan)

    ARSITEKTUR BLUEOS + COCKPIT:
    - Cockpit (GCS modern Blue Robotics) menggunakan WebRTC via port 6020 (internal BlueOS)
    - AI Dashboard menggunakan SDP / UDP port terpisah (default 5602) agar tidak konflik
    - RTSP endpoint tersedia di rtsp://192.168.2.2:8554/<nama_kamera>
"""

import os
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

    def open_sdp_stream(self, sdp_path: str) -> bool:
        """
        Membuka stream dari file .sdp (Session Description Protocol).
        File .sdp bisa diunduh langsung dari BlueOS Web UI -> Video Streams -> Download SDP.
        BlueOS (MAVLink Camera Manager) menghasilkan SDP yang berisi:
          - Codec: H264 / RTP
          - Target IP laptop (192.168.2.1)
          - Port: 5600 (Cockpit) atau port sekunder (5602 untuk AI Dashboard)
          - SPS/PPS parameter sets untuk decode H.264 tanpa negosiasi ulang
        """
        self.release()
        sdp_path = sdp_path.strip()

        # Jika input adalah path file .sdp yang ada di disk
        if sdp_path.lower().endswith(".sdp") and os.path.isfile(sdp_path):
            # Buka via FFMPEG dengan flag low-latency untuk RTP/UDP
            self.cap = cv2.VideoCapture(sdp_path, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                # Tuning buffer agar latency minimal
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return True

        # Fallback: coba buka sebagai URL biasa
        return self.open_network_stream(sdp_path)

    def open_network_stream(self, stream_url: str) -> bool:
        """
        Membuka network video stream (UDP / RTSP / HTTP).
        - udp://@:5602       -> mendengarkan port 5602 (endpoint AI Dashboard, bebas konflik Cockpit)
        - udp://@:5600       -> port default BlueOS (peringatan: bisa konflik dengan Cockpit)
        - rtsp://192.168.2.2:8554/video0 -> RTSP dari BlueOS Camera Manager
        """
        self.release()
        clean_url = stream_url.strip()

        # === RTSP: cara paling stabil & direkomendasikan BlueOS + Cockpit ===
        if clean_url.startswith("rtsp://"):
            self.cap = cv2.VideoCapture(clean_url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return True

        # === UDP: tuning FFMPEG agar H.264 RTP terbaca tanpa SDP ===
        if clean_url.startswith("udp://"):
            if "?" not in clean_url:
                # overrun_nonfatal=1 : jangan crash saat packet drop
                # fifo_size         : buffer paket UDP 50MB
                tuned_url = f"{clean_url}?overrun_nonfatal=1&fifo_size=50000000"
            else:
                tuned_url = clean_url

            self.cap = cv2.VideoCapture(tuned_url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return True

        # === Fallback: coba buka URL apapun via FFMPEG, lalu default backend ===
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
