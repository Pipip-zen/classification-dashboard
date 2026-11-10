"""
Page: 1_Live_Surveillance.py
Deskripsi:
    Live surveillance multimodal:
    - Screen Mirroring (Window Picker aplikasi ROV/Drone)
    - Virtual Testbench (Simulasi video offline untuk pengujian mingguan tanpa hardware berat)
    - Direct USB Camera / RTSP
"""

import time
import cv2
import numpy as np
import streamlit as st
from pathlib import Path

try:
    import pygetwindow as gw
    GW_AVAILABLE = True
except ImportError:
    GW_AVAILABLE = False

from core.detector import TacticalDetector
from core.stream_capture import StreamCapture
from core.distance_estimator import DistanceEstimator

st.set_page_config(page_title="Live Surveillance", page_icon="🛰️", layout="wide")

st.title("🛰️ Live Tactical Surveillance & Reconnaissance")
st.caption("Monitoring Live Feed ROV Bawah Air & Drone FPV Darat / Virtual Testbench")

# Setup Detector di Session State agar tidak reload berulang kali
if "detector" not in st.session_state:
    models_dir = Path("models")
    best_model = models_dir / "best.pt"
    model_to_load = str(best_model) if best_model.exists() else "yolov8n.pt"
    st.session_state.detector = TacticalDetector(model_path=model_to_load, conf_threshold=0.35)

detector: TacticalDetector = st.session_state.detector

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Konfigurasi Stream")
    feed_mode = st.radio(
        "Pilih Sumber Live Feed:",
        ["Virtual Testbench (Simulasi Offline)", "Screen Mirroring (Window ROV/Drone)", "Direct Camera / RTSP"]
    )

    st.divider()
    st.subheader("🎯 Parameter AI")
    conf_val = st.slider("Confidence Threshold", 0.10, 0.90, 0.35, 0.05)
    detector.conf_threshold = conf_val

    enable_dist = st.toggle("Aktifkan Estimasi Jarak", value=True)

    camera_opt = st.selectbox(
        "Profil Optik Kamera:",
        list(DistanceEstimator.CAMERA_PROFILES.keys()),
        format_func=lambda k: DistanceEstimator.CAMERA_PROFILES[k]["name"]
    )
    detector.distance_estimator.set_camera_profile(camera_opt)

# Layout Utama
col_video, col_telemetry = st.columns([3, 1])

with col_telemetry:
    st.subheader("📊 Telemetri Taktis")
    metric_env = st.empty()
    metric_hazard = st.empty()
    metric_neutral = st.empty()
    metric_fps = st.empty()
    alert_box = st.empty()

with col_video:
    frame_placeholder = st.empty()

stream_cap = StreamCapture()
is_active = False

if feed_mode == "Virtual Testbench (Simulasi Offline)":
    st.info("💡 **Mode Testbench Mingguan:** Memutar rekaman video patroli secara otomatis (*infinite loop*) untuk pengujian tanpa membawa ROV/drone fisik.")
    
    # Deteksi video sampel di testbench_samples/videos/
    video_dir = Path("testbench_samples/videos")
    available_videos = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.avi"))

    if not available_videos:
        st.warning("Belum ada video di folder `testbench_samples/videos/`. Silakan letakkan rekaman MP4 Anda di sana, atau gunakan menu upload di halaman Media Analysis.")
        uploaded_tb = st.file_uploader("Atau unggah video simulasi di sini:", type=["mp4", "avi"])
        if uploaded_tb:
            temp_path = video_dir / uploaded_tb.name
            video_dir.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(uploaded_tb.read())
            st.success("Video berhasil diunggah! Merefresh...")
            st.rerun()
    else:
        sel_video = st.selectbox("Pilih Skenario Video Uji:", available_videos, format_func=lambda p: p.name)
        start_btn = st.button("▶️ Mulai Streaming Simulasi", type="primary")

        if start_btn:
            is_active = stream_cap.open_video_file(str(sel_video))

elif feed_mode == "Screen Mirroring (Window ROV/Drone)":
    st.info("💡 **Mode Screen Mirroring:** Menangkap langsung window aplikasi pengendali ROV (misal QGroundControl) atau video player.")
    
    window_titles = []
    if GW_AVAILABLE:
        window_titles = [w.title for w in gw.getAllWindows() if w.title.strip() != ""]

    if window_titles:
        selected_window_title = st.selectbox("Pilih Window Aplikasi Aktif:", window_titles)
        start_mirror = st.button("▶️ Mulai Tangkap Window", type="primary")

        if start_mirror:
            target_win = gw.getWindowsWithTitle(selected_window_title)[0]
            if target_win:
                is_active = True
                st.session_state["mirror_win"] = target_win
    else:
        st.warning("Tidak dapat mendeteksi daftar window. Pastikan modul pygetwindow terinstal.")

elif feed_mode == "Direct Camera / RTSP":
    cam_source = st.text_input("Camera Index (0/1) atau RTSP Stream URL:", value="0")
    start_cam = st.button("▶️ Buka Kamera", type="primary")
    if start_cam:
        idx = int(cam_source) if cam_source.isdigit() else cam_source
        is_active = stream_cap.open_camera(idx)

# Loop Streaming
if is_active:
    stop_btn = st.button("⏹️ Hentikan Stream")
    prev_time = time.time()

    while not stop_btn:
        if feed_mode == "Virtual Testbench (Simulasi Offline)":
            ret, frame = stream_cap.read_virtual_loop_frame()
        elif feed_mode == "Screen Mirroring (Window ROV/Drone)":
            win = st.session_state.get("mirror_win")
            if win:
                frame = stream_cap.capture_screen_region(
                    top=win.top, left=win.left, width=win.width, height=win.height
                )
                ret = (frame is not None)
            else:
                ret = False
        else:
            ret, frame = stream_cap.read_frame()

        if not ret or frame is None:
            break

        # AI Detection & Threat Evaluation
        results = detector.detect(frame, enable_distance=enable_dist)
        annotated = results["annotated_frame"]

        # Hitung FPS
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time + 1e-6)
        prev_time = curr_time

        # Update Video Display
        frame_placeholder.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)

        # Update Telemetri
        metric_env.metric("Domain Lingkungan", results["environment"])
        metric_hazard.metric("🚨 Target Bahaya (Hazard)", results["hazard_count"])
        metric_neutral.metric("🟢 Target Netral (Aman)", results["neutral_count"])
        metric_fps.metric("Kecepatan Pemrosesan", f"{int(fps)} FPS")

        if results["hazard_count"] > 0:
            alert_box.error(f"⚠️ PERINGATAN: Terdeteksi {results['hazard_count']} objek ancaman berbahaya di area pengamatan!")
        else:
            alert_box.success("✅ Area Aman: Tidak ada ancaman terdeteksi.")

        time.sleep(0.01)

    stream_cap.release()

