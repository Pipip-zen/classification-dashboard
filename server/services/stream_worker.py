"""
Module: server/services/stream_worker.py
Deskripsi:
    Manajer pipeline video multi-channel ('drone' dan 'rov'):
    - Mode Browser Push: Terima frame JPEG biner via WSS dengan Async Latest-Frame + Box Cache
    - Mode Server Pull: Testbench MP4, RTSP/UDP/SDP, YouTube, TikTok, Webcam
    - Output JPEG resolusi utama & Mini Preview (PiP) terpisah untuk Spectator
"""

import time
import threading
import asyncio
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.stream_capture import StreamCapture
from core.detector import TacticalDetector
from server.state import state, ChannelState, VALID_CHANNELS


class ChannelWorker:
    """Worker independen untuk satu channel taktis ('drone' atau 'rov')."""

    def __init__(self, channel_id: str, channel_state: ChannelState):
        self.channel_id = channel_id
        self.channel = channel_state
        self.stream_capture = StreamCapture()

        self.pull_thread: Optional[threading.Thread] = None
        self.ai_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        self.frame_lock = threading.Lock()
        self.screen_win = None

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.videos_dir = self.base_dir / "testbench_samples" / "videos"

        # Selalu simpan hanya frame terakhir agar latensi CPU tidak menumpuk saat antre
        self._pending_infer_frame: Optional[np.ndarray] = None
        self._infer_event = threading.Event()

        self._standby_jpeg = self._generate_standby_frame(
            f"{channel_id.upper()} CHANNEL STANDBY // WAITING FOR FEED"
        )
        standby_bgr = cv2.imdecode(np.frombuffer(self._standby_jpeg, np.uint8), cv2.IMREAD_COLOR)
        self._standby_pip_jpeg = self._encode_pip_from_bgr(standby_bgr)
        self.latest_jpeg: bytes = self._standby_jpeg
        self.latest_pip_jpeg: bytes = self._standby_pip_jpeg
        self.frame_seq: int = 0

        self._vid_count = 0
        self._vid_fps_t0 = time.time()
        self._ai_count = 0
        self._ai_fps_t0 = time.time()

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    @staticmethod
    def _encode_pip_from_bgr(frame: Optional[np.ndarray]) -> bytes:
        if frame is None or frame.size == 0:
            return b""
        h, w = frame.shape[:2]
        target_w = 420
        if w > target_w:
            scale = target_w / float(w)
            pip_frame = cv2.resize(frame, (target_w, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
        else:
            pip_frame = frame
        _, buf = cv2.imencode(".jpg", pip_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 58])
        return buf.tobytes()

    def _generate_standby_frame(self, message: str) -> bytes:
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:] = (10, 14, 20)

        for x in range(0, 1280, 80):
            cv2.line(img, (x, 0), (x, 720), (20, 30, 42), 1)
        for y in range(0, 720, 80):
            cv2.line(img, (0, y), (1280, y), (20, 30, 42), 1)

        cx, cy = 640, 360
        accent = (0, 229, 255) if self.channel_id == "rov" else (0, 255, 128)
        cv2.circle(img, (cx, cy), 60, accent, 1)
        cv2.circle(img, (cx, cy), 120, accent, 1)
        cv2.line(img, (cx - 150, cy), (cx + 150, cy), accent, 1)
        cv2.line(img, (cx, cy - 150), (cx, cy + 150), accent, 1)

        def draw_centered(text: str, y: int, scale: float, color: tuple, thickness: int):
            (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
            cv2.putText(
                img, text, ((1280 - tw) // 2, y),
                cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA
            )

        draw_centered(f"VANGUARD AI // {self.channel_id.upper()} GCS", cy - 185, 0.9, accent, 2)
        draw_centered(message, cy + 205, 0.72, accent, 2)
        draw_centered("MODE: SIAP SIARAN / MENUNGGU OPERATOR", cy + 240, 0.5, (148, 163, 184), 1)

        _, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return buf.tobytes()

    def start_browser_ingest(self, source_label: str = "Browser Window Capture") -> Dict[str, Any]:
        """Mengaktifkan mode ingest push langsung dari browser Operator."""
        with self.lock:
            self.stop_stream()
            self.channel.source_type = "browser_push"
            self.channel.source_param = source_label
            self.channel.stream_active = True
            self.channel.reset_tracking_state()
            self._reset_counters()
            self.running = True
            self.ai_thread = threading.Thread(target=self._ai_infer_loop, daemon=True)
            self.ai_thread.start()
            return {"success": True, "channel_id": self.channel_id, "source_type": "browser_push"}

    def start_stream(self, source_type: str, source_param: str) -> Dict[str, Any]:
        """Memulai stream tarik sisi server (testbench, network, youtube, tiktok, webcam)."""
        with self.lock:
            self.stop_stream()

            success = False
            error_msg = ""

            try:
                if source_type == "testbench":
                    vid_file = self.videos_dir / source_param
                    if not vid_file.exists():
                        vids = list(self.videos_dir.glob("*.mp4"))
                        if vids:
                            vid_file = vids[0]
                    if vid_file.exists():
                        success = self.stream_capture.open_video_file(str(vid_file))
                    else:
                        error_msg = f"Berkas video tidak ditemukan: {source_param}"

                elif source_type == "youtube":
                    success, title_or_err = self.stream_capture.open_youtube_stream(source_param)
                    if not success:
                        error_msg = f"Gagal membuka YouTube stream: {title_or_err}"

                elif source_type == "tiktok":
                    success, title_or_err = self.stream_capture.open_tiktok_stream(source_param)
                    if not success:
                        error_msg = f"Gagal membuka TikTok live: {title_or_err}"

                elif source_type == "network":
                    if source_param.lower().endswith(".sdp"):
                        success = self.stream_capture.open_sdp_stream(source_param)
                    else:
                        success = self.stream_capture.open_network_stream(source_param)
                    if not success:
                        error_msg = f"Gagal membuka network stream: {source_param}"

                elif source_type == "webcam":
                    idx = int(source_param) if source_param.isdigit() else 0
                    success = self.stream_capture.open_camera(idx)
                    if not success:
                        error_msg = f"Gagal membuka webcam pada indeks {idx}"

                elif source_type == "screen":
                    try:
                        import pygetwindow as gw
                        matching = gw.getWindowsWithTitle(source_param)
                        if matching:
                            self.screen_win = matching[0]
                            success = True
                        else:
                            error_msg = f"Jendela tidak ditemukan: {source_param}"
                    except Exception as e:
                        error_msg = str(e)

                if success:
                    self.channel.source_type = source_type
                    self.channel.source_param = source_param
                    self.channel.stream_active = True
                    self.channel.reset_tracking_state()
                    self._reset_counters()
                    self.running = True

                    self.ai_thread = threading.Thread(target=self._ai_infer_loop, daemon=True)
                    self.ai_thread.start()
                    self.pull_thread = threading.Thread(target=self._run_pull_loop, daemon=True)
                    self.pull_thread.start()
                    return {
                        "success": True,
                        "channel_id": self.channel_id,
                        "source_type": source_type,
                        "source_param": source_param,
                    }

                return {"success": False, "error": error_msg or "Gagal menginisialisasi stream"}

            except Exception as e:
                return {"success": False, "error": str(e)}

    def stop_stream(self):
        self.running = False
        self._infer_event.set()

        if self.pull_thread and self.pull_thread.is_alive():
            self.pull_thread.join(timeout=1.0)
        if self.ai_thread and self.ai_thread.is_alive():
            self.ai_thread.join(timeout=1.0)

        self.pull_thread = None
        self.ai_thread = None
        self.screen_win = None
        self._pending_infer_frame = None
        self._infer_event.clear()

        self.stream_capture.release()
        self.channel.stream_active = False
        self.channel.current_fps = 0.0
        self.channel.ai_fps = 0.0
        self.channel.last_latency_ms = 0.0
        self.channel.reset_tracking_state()
        self.channel.orientation_estimator.set_north()

        self.latest_jpeg = self._standby_jpeg
        self.latest_pip_jpeg = self._standby_pip_jpeg
        self.frame_seq += 1

        self.channel.latest_telemetry = self.channel._default_telemetry()
        self._schedule_broadcast(self.channel.latest_telemetry)

    def _reset_counters(self):
        now = time.time()
        self._vid_count = 0
        self._vid_fps_t0 = now
        self._ai_count = 0
        self._ai_fps_t0 = now
        self.channel.latest_telemetry["heading_deg"] = 0.0
        self.channel.latest_telemetry["cardinal"] = "N"
        self.channel.latest_telemetry["turn_rate_dps"] = 0.0
        self.channel.latest_telemetry["stream_active"] = True

    def get_latest_frame(self, pip: bool = False) -> bytes:
        if pip:
            return self.latest_pip_jpeg or self._standby_pip_jpeg
        return self.latest_jpeg or self._standby_jpeg

    def push_browser_frame(self, jpeg_bytes: bytes) -> Dict[str, Any]:
        """Menerima frame JPEG biner dari browser Operator dan langsung render overlay terbaru."""
        arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            return self.channel.latest_telemetry

        h, w = frame.shape[:2]
        if w > 1280 or h > 720:
            scale = min(1280.0 / w, 720.0 / h)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        self._process_incoming_frame(frame)
        return self.channel.latest_telemetry

    def _process_incoming_frame(self, frame: np.ndarray) -> None:
        # Serahkan salinan frame terbaru ke AI worker dan langsung tempel cache box untuk output mulus
        with self.frame_lock:
            self._pending_infer_frame = frame
            self._infer_event.set()
            cached_dets = list(self.channel.cached_detections)

        heading_info = self.channel.orientation_estimator.update(frame)

        annotated = TacticalDetector.render_overlay(
            frame,
            cached_dets,
            mode=self.channel_id,
            draw_hud_reticle=self.channel.reticle_visible,
            show_labels=self.channel.labels_visible,
            enable_dusk=self.channel.dusk_enhancer,
            enable_clahe=False,
        )

        _, jpeg_buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        pip_bytes = self._encode_pip_from_bgr(annotated)

        self.latest_jpeg = jpeg_buf.tobytes()
        if pip_bytes:
            self.latest_pip_jpeg = pip_bytes
        self.frame_seq += 1

        self._vid_count += 1
        now = time.time()
        if now - self._vid_fps_t0 >= 1.0:
            self.channel.current_fps = round(self._vid_count / (now - self._vid_fps_t0), 1)
            self._vid_count = 0
            self._vid_fps_t0 = now

        h, w = frame.shape[:2]
        with self.channel.lock:
            self.channel.latest_telemetry = {
                **self.channel.latest_telemetry,
                "stream_active": True,
                "fps": self.channel.current_fps,
                "frame_size": {"width": w, "height": h},
                "heading_deg": heading_info.get("heading_deg", 0.0),
                "cardinal": heading_info.get("cardinal", "N"),
                "turn_rate_dps": heading_info.get("turn_rate_dps", 0.0),
                "compass_calibrated": heading_info.get("is_calibrated", False),
                "tracked_compass_points": heading_info.get("tracked_points", 0),
            }

    def _ai_infer_loop(self):
        """Worker AI asinkron yang memproses frame terbaru secepat kemampuan CPU/GPU."""
        while self.running:
            triggered = self._infer_event.wait(timeout=0.1)
            if not self.running:
                break
            if not triggered:
                continue

            with self.frame_lock:
                frame = self._pending_infer_frame
                self._pending_infer_frame = None
                self._infer_event.clear()

            if frame is None or frame.size == 0:
                continue

            h, w = frame.shape[:2]
            t_start = time.time()
            res = state.detector.detect(
                frame,
                enable_distance=True,
                mode=self.channel_id,
                draw_hud_reticle=False,
                show_labels=False,
                enable_dusk=self.channel.dusk_enhancer,
                tracker=self.channel.tracker,
                conf_threshold=self.channel.confidence_gate,
            )
            infer_ms = (time.time() - t_start) * 1000.0

            raw_dets = res.get("detections", [])
            hazard_count = res.get("hazard_count", 0)
            neutral_count = res.get("neutral_count", 0)
            threat_level = "RED SECTOR" if hazard_count > 0 else "GREEN SECTOR"
            threat_color_hex = "#FF3B30" if hazard_count > 0 else "#00FF66"

            valid_dets: List[Dict[str, Any]] = []
            for d in raw_dets:
                cls_id = d.get("class_id", 0)
                info = state.threat_evaluator.get_info_by_class_id(cls_id)
                box = d.get("box", [0, 0, 0, 0])
                box_w = max(1.0, float(box[2] - box[0]))
                est_dist = self.channel.distance_estimator.estimate_distance(box_w, class_id=cls_id)

                valid_dets.append({
                    "track_id": d.get("track_id", 0),
                    "class_id": cls_id,
                    "class_name": d.get("class_name", ""),
                    "display_name": d.get("display_name", ""),
                    "confidence": round(float(d.get("confidence", 0.0)), 2),
                    "bbox": box,
                    "threat": d.get("threat", "NEUTRAL"),
                    "threat_label": d.get("threat_label", ""),
                    "color_hex": info.get("color_hex", "#00FF66"),
                    "color_bgr": info.get("color_bgr", [0, 255, 102]),
                    "estimated_distance_m": round(est_dist, 1) if est_dist else None,
                })

            self._ai_count += 1
            now = time.time()
            if now - self._ai_fps_t0 >= 1.0:
                self.channel.ai_fps = round(self._ai_count / (now - self._ai_fps_t0), 1)
                self._ai_count = 0
                self._ai_fps_t0 = now
            self.channel.last_latency_ms = round(infer_ms, 1)

            with self.frame_lock:
                self.channel.cached_detections = valid_dets
                self.channel.cached_hazard_count = hazard_count
                self.channel.cached_neutral_count = neutral_count
                self.channel.cached_threat_level = threat_level
                self.channel.cached_threat_color_hex = threat_color_hex

            client_dets = [
                {k: v for k, v in det.items() if k != "color_bgr"} for det in valid_dets
            ]
            with self.channel.lock:
                payload = {
                    **self.channel.latest_telemetry,
                    "channel_id": self.channel_id,
                    "cockpit_mode": self.channel_id,
                    "stream_active": True,
                    "threat_level": threat_level,
                    "threat_color_hex": threat_color_hex,
                    "total_objects": len(client_dets),
                    "hazard_count": hazard_count,
                    "neutral_count": neutral_count,
                    "fps": self.channel.current_fps,
                    "ai_fps": self.channel.ai_fps,
                    "latency_ms": self.channel.last_latency_ms,
                    "source_type": self.channel.source_type,
                    "source_param": self.channel.source_param,
                    "confidence_gate": self.channel.confidence_gate,
                    "dusk_enhancer": self.channel.dusk_enhancer,
                    "frame_size": {"width": w, "height": h},
                    "owner_locked": not self.channel.is_lock_expired(),
                    "owner_label": self.channel.owner_label,
                    "detections": client_dets,
                }
                self.channel.latest_telemetry = payload
            self._schedule_broadcast(payload)

    def _run_pull_loop(self):
        """Loop pembacaan video untuk sumber tarik sisi server (testbench, network, webcam, dll)."""
        while self.running:
            loop_start = time.time()

            if self.channel.source_type == "screen" and self.screen_win is not None:
                try:
                    w = max(10, self.screen_win.width)
                    h = max(10, self.screen_win.height)
                    l, t = self.screen_win.left, self.screen_win.top
                    frame = self.stream_capture.capture_screen_region(top=t, left=l, width=w, height=h)
                    ret = frame is not None
                except Exception:
                    ret, frame = False, None
            elif self.channel.source_type == "testbench":
                ret, frame = self.stream_capture.read_virtual_loop_frame()
            else:
                ret, frame = self.stream_capture.read_frame()

            if not ret or frame is None:
                time.sleep(0.03)
                continue

            self._process_incoming_frame(frame)
            self._schedule_broadcast(self.channel.latest_telemetry)

            elapsed = time.time() - loop_start
            time.sleep(max(0.001, (1.0 / 25.0) - elapsed))

    def _schedule_broadcast(self, telemetry: Dict[str, Any]):
        if self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    state.broadcast_telemetry(telemetry, channel_id=self.channel_id),
                    self.loop,
                )
            except Exception:
                pass


class MultiStreamManager:
    """Mengelola worker paralel Drone & ROV sekaligus menjaga kompatibilitas interface tunggal."""

    def __init__(self):
        self.workers: Dict[str, ChannelWorker] = {
            cid: ChannelWorker(cid, state.get_channel(cid)) for cid in VALID_CHANNELS
        }

    def get_worker(self, channel_id: Optional[str] = None) -> ChannelWorker:
        cid = (channel_id or state.active_channel_id).lower()
        if cid not in self.workers:
            cid = state.active_channel_id
        return self.workers[cid]

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        for worker in self.workers.values():
            worker.set_event_loop(loop)

    def start_stream(self, source_type: str, source_param: str, channel_id: Optional[str] = None) -> Dict[str, Any]:
        return self.get_worker(channel_id).start_stream(source_type, source_param)

    def stop_stream(self, channel_id: Optional[str] = None):
        self.get_worker(channel_id).stop_stream()

    def stop_all(self):
        for worker in self.workers.values():
            worker.stop_stream()

    def get_latest_frame(self, channel_id: Optional[str] = None, pip: bool = False) -> bytes:
        return self.get_worker(channel_id).get_latest_frame(pip=pip)


stream_worker = MultiStreamManager()
