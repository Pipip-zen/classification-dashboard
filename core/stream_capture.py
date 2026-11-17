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

    def open_youtube_stream(self, youtube_url: str, max_height: int = 720) -> Tuple[bool, str]:
        """
        Mengekstrak dan membuka live stream atau video dari YouTube menggunakan yt-dlp.
        Menggunakan format bestvideo teroptimasi (max 720p) agar ringan dan responsif.
        """
        self.release()
        clean_url = youtube_url.strip()
        if not clean_url:
            return False, "URL YouTube kosong."

        try:
            import yt_dlp
        except ImportError:
            return False, "Pustaka 'yt-dlp' belum terinstal."

        ydl_opts = {
            'format': f'bestvideo[height<={max_height}]/bestvideo/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
                stream_url = info.get('url')
                title = info.get('title', 'YouTube Video')

                if not stream_url:
                    return False, "Tidak dapat mengekstrak direct stream URL dari video ini."

                # Buka direct video stream URL di OpenCV via FFMPEG backend
                self.cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(stream_url)

                if self.cap.isOpened():
                    return True, title
                else:
                    return False, "OpenCV gagal membuka stream URL YouTube."
        except Exception as e:
            return False, f"Gagal mengekstrak YouTube: {str(e)}"

    def capture_screen_region(
        self,
        top: int = 100,
        left: int = 100,
        width: int = 1280,
        height: int = 720,
        target_max_w: int = 1280,
        target_max_h: int = 720
    ) -> Optional[np.ndarray]:
        if not MSS_AVAILABLE or self.sct is None:
            return None

        # Validasi batas koordinat agar tidak crash jika window berkoordinat negatif / minimized
        if width <= 50 or height <= 50:
            return None
        safe_top = max(0, int(top))
        safe_left = max(0, int(left))
        safe_width = max(100, int(width))
        safe_height = max(100, int(height))

        monitor = {"top": safe_top, "left": safe_left, "width": safe_width, "height": safe_height}
        try:
            sct_img = self.sct.grab(monitor)
            frame = np.array(sct_img)
            bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # Optimasi Performa: Downscale jika resolusi window melebihi 720p (mengurangi lag CPU)
            cur_h, cur_w = bgr.shape[:2]
            if cur_w > target_max_w or cur_h > target_max_h:
                scale = min(target_max_w / cur_w, target_max_h / cur_h)
                new_w = int(cur_w * scale)
                new_h = int(cur_h * scale)
                bgr = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

            return bgr
        except Exception:
            return None

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
