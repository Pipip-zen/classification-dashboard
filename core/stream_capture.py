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
import re
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

    def open_tiktok_stream(self, tiktok_input: str) -> Tuple[bool, str]:
        """
        Mengekstrak dan membuka live stream TikTok:
        - Menerima format:
          1. https://www.tiktok.com/@username/live
          2. @username atau username
          3. Direct pull stream URL (FLV / M3U8)
        """
        self.release()
        clean_input = tiktok_input.strip()
        if not clean_input:
            return False, "Input target TikTok kosong."

        # 1. Direct pull URL (FLV / M3U8)
        if clean_input.startswith("http://") or clean_input.startswith("https://"):
            if ".flv" in clean_input or ".m3u8" in clean_input or "pull" in clean_input:
                self.cap = cv2.VideoCapture(clean_input, cv2.CAP_FFMPEG)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(clean_input)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    return True, "Direct TikTok FLV/HLS Stream"

        # 2. Format URL akun TikTok
        if clean_input.startswith("@"):
            tiktok_url = f"https://www.tiktok.com/{clean_input}/live"
        elif not clean_input.startswith("http://") and not clean_input.startswith("https://"):
            tiktok_url = f"https://www.tiktok.com/@{clean_input}/live"
        else:
            tiktok_url = clean_input

        try:
            import yt_dlp
        except ImportError:
            return False, "Pustaka 'yt-dlp' belum terinstal."

        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(tiktok_url, download=False)
                stream_url = info.get('url')
                title = info.get('title') or info.get('uploader') or clean_input

                if not stream_url:
                    formats = info.get('formats', [])
                    if formats:
                        stream_url = formats[-1].get('url')

                if not stream_url:
                    return False, "Tidak dapat menemukan link video stream. Kemungkinan siaran langsung sedang offline atau akun diprivat."

                self.cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(stream_url)

                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    return True, f"Live @{title}"
                else:
                    return False, "OpenCV gagal membuka stream URL TikTok."
        except Exception as e:
            err_msg = str(e)
            # Bersihkan escape sequence ANSI terminal jika ada
            clean_err = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', err_msg).strip()
            clean_err = clean_err.replace("[0;31m", "").replace("[0m", "")

            lower_err = clean_err.lower()
            if any(k in lower_err for k in ["offline", "not currently live", "is not live", "channel is not live", "not live"]):
                return False, f"Akun '{clean_input}' sedang OFFLINE (tidak menyiarkan Live). Pastikan akun sedang aktif live, atau buka live di browser lalu gunakan mode 'Screen Capture' di GCS."
            if "captcha" in lower_err or "verify" in lower_err or "blocked" in lower_err:
                return False, "TikTok membatasi akses bot (Captcha). Solusi praktis: buka Live di browser Anda, lalu pilih mode 'Screen Capture' di GCS."
            return False, f"Gagal mengekstrak stream TikTok: {clean_err}"

    def capture_screen_region(
        self,
        top: int = 100,
        left: int = 100,
        width: int = 1280,
        height: int = 720,
        *args,
        **kwargs
    ) -> Optional[np.ndarray]:
        if not MSS_AVAILABLE or self.sct is None:
            return None

        target_max_w = int(kwargs.get("target_max_w", 1280))
        target_max_h = int(kwargs.get("target_max_h", 720))

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
