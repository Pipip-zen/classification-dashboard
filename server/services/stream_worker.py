"""
Module: server/services/stream_worker.py
Deskripsi:
    Worker thread untuk pemrosesan video pipeline real-time:
    - Menangkap frame dari StreamCapture (Virtual Testbench, YouTube, RTSP, Screen, Webcam, TikTok)
    - Menjalankan TacticalDetector AI (YOLOv8 + CUDA)
    - Menjalankan ThreatEvaluator (ROV vs Drone logic + Foliage Guard) & DistanceEstimator
    - Menerapkan Dusk Enhancer jika diaktifkan
    - Menyediakan buffer frame MJPEG berlatensi rendah
    - Menyiarkan telemetri JSON secara asinkron ke WebSocket client
"""

import time
import threading
import asyncio
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.stream_capture import StreamCapture
from server.state import state


class StreamWorker:
    def __init__(self):
        self.stream_capture = StreamCapture()
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        self.screen_win = None
        
        self.latest_jpeg: Optional[bytes] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.videos_dir = self.base_dir / "testbench_samples" / "videos"
        
        # Buat placeholder standby frame taktis
        self._standby_jpeg = self._generate_standby_frame()
        self.latest_jpeg = self._standby_jpeg

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def _generate_standby_frame(self, message: str = "VANGUARD TACTICAL STANDBY // WAITING FOR FEED") -> bytes:
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:] = (10, 14, 20)  # Dark slate background
        
        # Grid tactical halus
        for x in range(0, 1280, 80):
            cv2.line(img, (x, 0), (x, 720), (20, 30, 42), 1)
        for y in range(0, 720, 80):
            cv2.line(img, (0, y), (1280, y), (20, 30, 42), 1)
            
        # Reticle tengah
        cx, cy = 640, 360
        cv2.circle(img, (cx, cy), 60, (0, 229, 255), 1)
        cv2.circle(img, (cx, cy), 120, (0, 229, 255), 1)
        cv2.line(img, (cx - 150, cy), (cx + 150, cy), (0, 229, 255), 1)
        cv2.line(img, (cx, cy - 150), (cx, cy + 150), (0, 229, 255), 1)
        
        # Helper untuk menempatkan teks tepat di tengah secara horizontal
        def draw_centered(text: str, y: int, font, scale: float, color: tuple, thickness: int):
            (w, _), _ = cv2.getTextSize(text, font, scale, thickness)
            x = (1280 - w) // 2
            cv2.putText(img, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)

        # Header VANGUARD AI
        draw_centered("VANGUARD AI // TACTICAL GCS", cy - 190,
                      cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 229, 255), 2)
        draw_centered("VISUAL AI FOR NEUTRALIZATION & GROUND-AQUATIC RECONNAISSANCE", cy - 160,
                      cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 149, 237), 1)

        # Teks Standby & Status
        draw_centered(message, cy + 205,
                      cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 128), 2)
        draw_centered("STATUS: READY // SELECT SOURCE IN VANGUARD HUD", cy + 240,
                      cv2.FONT_HERSHEY_SIMPLEX, 0.52, (100, 116, 139), 1)
        
        _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return buf.tobytes()

    def start_stream(self, source_type: str, source_param: str) -> Dict[str, Any]:
        with self.lock:
            self.stop_stream()
            
            success = False
            error_msg = ""
            
            try:
                if source_type == "testbench":
                    vid_file = self.videos_dir / source_param
                    if not vid_file.exists():
                        # Coba cari file pertama yang ada
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
                    state.source_type = source_type
                    state.source_param = source_param
                    state.stream_active = True
                    state.orientation_estimator.reset()
                    self.running = True
                    self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
                    self.worker_thread.start()
                    return {"success": True, "source_type": source_type, "source_param": source_param}
                else:
                    return {"success": False, "error": error_msg or "Gagal menginisialisasi stream"}

            except Exception as e:
                return {"success": False, "error": str(e)}

    def stop_stream(self):
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
        self.worker_thread = None
        self.stream_capture.release()
        state.orientation_estimator.reset()
        state.orientation_estimator.set_north()
        state.stream_active = False
        state.current_fps = 0.0
        self.latest_jpeg = self._standby_jpeg

        # Reset telemetri navigasi dan target ke 0 / N saat stream berhenti
        state.latest_telemetry["heading_deg"] = 0.0
        state.latest_telemetry["cardinal"] = "N"
        state.latest_telemetry["turn_rate_dps"] = 0.0
        state.latest_telemetry["total_objects"] = 0
        state.latest_telemetry["hazard_count"] = 0
        state.latest_telemetry["neutral_count"] = 0
        state.latest_telemetry["detections"] = []

        if self.loop and self.loop.is_running() and state.active_websockets:
            try:
                asyncio.run_coroutine_threadsafe(
                    state.broadcast_telemetry(state.latest_telemetry),
                    self.loop
                )
            except Exception:
                pass

    def get_latest_frame(self) -> bytes:
        if self.latest_jpeg is not None:
            return self.latest_jpeg
        return self._standby_jpeg

    def _run_loop(self):
        fps_counter = 0
        fps_start = time.time()
        last_calc_fps = 0.0

        while self.running:
            loop_start = time.time()
            
            if state.source_type == "screen" and self.screen_win is not None:
                try:
                    w = max(10, self.screen_win.width)
                    h = max(10, self.screen_win.height)
                    l, t = self.screen_win.left, self.screen_win.top
                    frame = self.stream_capture.capture_screen_region(top=t, left=l, width=w, height=h)
                    ret = frame is not None
                except Exception:
                    ret, frame = False, None
            elif state.source_type == "testbench":
                ret, frame = self.stream_capture.read_virtual_loop_frame()
            else:
                ret, frame = self.stream_capture.read_frame()

            if not ret or frame is None:
                time.sleep(0.03)
                continue

            h, w = frame.shape[:2]
            
            # Set confidence threshold pada detector
            state.detector.conf_threshold = state.confidence_gate

            # Inferensi AI Terpadu via TacticalDetector.detect()
            t_infer_start = time.time()
            res = state.detector.detect(
                frame,
                enable_distance=True,
                mode=state.cockpit_mode,
                draw_hud_reticle=state.reticle_visible,
                show_labels=state.labels_visible,
                enable_dusk=state.dusk_enhancer
            )
            infer_latency = (time.time() - t_infer_start) * 1000.0

            annotated_frame = res.get("annotated_frame", frame)
            raw_dets = res.get("detections", [])
            hazard_count = res.get("hazard_count", 0)
            neutral_count = res.get("neutral_count", 0)
            threat_level = "RED SECTOR" if hazard_count > 0 else "GREEN SECTOR"
            threat_color_hex = "#FF3B30" if hazard_count > 0 else "#00FF66"

            # Enrich dengan estimasi jarak pinhole & color_hex
            valid_dets = []
            for d in raw_dets:
                cls_id = d.get("class_id", 0)
                info = state.threat_evaluator.get_info_by_class_id(cls_id)
                box = d.get("box", [0, 0, 0, 0])
                box_w = max(1.0, float(box[2] - box[0]))
                est_dist = state.distance_estimator.estimate_distance(box_w, class_id=cls_id)
                
                valid_dets.append({
                    "class_id": cls_id,
                    "class_name": d.get("class_name", ""),
                    "display_name": d.get("display_name", ""),
                    "confidence": round(float(d.get("confidence", 0.0)), 2),
                    "bbox": box,
                    "threat": d.get("threat", "NEUTRAL"),
                    "threat_label": d.get("threat_label", ""),
                    "color_hex": info.get("color_hex", "#00FF66"),
                    "estimated_distance_m": round(est_dist, 1) if est_dist else None
                })

            # Hitung FPS
            fps_counter += 1
            if time.time() - fps_start >= 1.0:
                last_calc_fps = fps_counter / (time.time() - fps_start)
                fps_counter = 0
                fps_start = time.time()
                state.current_fps = round(last_calc_fps, 1)
                state.last_latency_ms = round(infer_latency, 1)

            # Estimasi Orientasi / Kompas Visual (Optical Flow Yaw Tracking)
            heading_info = state.orientation_estimator.update(frame)

            # Encode ke JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            _, jpeg_buf = cv2.imencode('.jpg', annotated_frame, encode_param)
            self.latest_jpeg = jpeg_buf.tobytes()

            # Susun Payload Telemetri untuk WebSocket
            telemetry_payload = {
                "cockpit_mode": state.cockpit_mode,
                "threat_level": threat_level,
                "threat_color_hex": threat_color_hex,
                "total_objects": len(valid_dets),
                "hazard_count": hazard_count,
                "neutral_count": neutral_count,
                "fps": state.current_fps,
                "latency_ms": state.last_latency_ms,
                "source_type": state.source_type,
                "source_param": state.source_param,
                "confidence_gate": state.confidence_gate,
                "dusk_enhancer": state.dusk_enhancer,
                "frame_size": {"width": w, "height": h},
                "heading_deg": heading_info.get("heading_deg", 0.0),
                "cardinal": heading_info.get("cardinal", "N"),
                "turn_rate_dps": heading_info.get("turn_rate_dps", 0.0),
                "compass_calibrated": heading_info.get("is_calibrated", False),
                "tracked_compass_points": heading_info.get("tracked_points", 0),
                "detections": valid_dets
            }
            state.latest_telemetry = telemetry_payload

            # Broadcast ke WebSocket
            if self.loop and self.loop.is_running() and state.active_websockets:
                asyncio.run_coroutine_threadsafe(
                    state.broadcast_telemetry(telemetry_payload),
                    self.loop
                )

            # Jaga framerate loop (~28-30 FPS)
            elapsed = time.time() - loop_start
            sleep_time = max(0.001, (1.0 / 30.0) - elapsed)
            time.sleep(sleep_time)


stream_worker = StreamWorker()
