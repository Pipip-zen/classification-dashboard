"""
Page: 1_Live_Surveillance.py
Deskripsi:
    TACTICAL COMMAND COCKPIT (FOKUS MURNI IMAGE CLASSIFICATION & OBJECT DETECTION)
    Pemisahan Mode Operasional Penuh:
    - 🔵 MODE ROV: Danau & Eksplorasi Bawah Air (Submarine, Biota/Ikan, Karang, ROV, Kapal)
    - 🟢 MODE DRONE: Pemantauan Udara & Spectator (Prajurit Tim A vs Tim B, Kendaraan, Sipil)
"""

import time
import cv2
import numpy as np
import streamlit as st
from datetime import datetime
from pathlib import Path

try:
    import pygetwindow as gw
    GW_AVAILABLE = True
except ImportError:
    GW_AVAILABLE = False

from core.detector import TacticalDetector
from core.stream_capture import StreamCapture

st.set_page_config(page_title="Tactical Cockpit", page_icon="🛡️", layout="wide")

# =========================================================================
# TACTICAL MILITARY HUD CSS STYLING
# =========================================================================
st.markdown("""
<style>
    .stApp {
        background-color: #06090F;
    }
    
    .tactical-header {
        background: linear-gradient(90deg, rgba(19, 28, 46, 0.9) 0%, rgba(10, 14, 23, 0.95) 100%);
        border: 1px solid #1E293B;
        border-left: 4px solid #00E5FF;
        border-radius: 6px;
        padding: 12px 20px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0, 229, 255, 0.08);
    }
    .tactical-title {
        font-family: 'Courier New', monospace;
        font-weight: 800;
        letter-spacing: 2px;
        color: #F8FAFC;
        font-size: 1.3rem;
        margin: 0;
    }
    .tactical-badge {
        font-family: monospace;
        font-size: 0.75rem;
        padding: 3px 8px;
        border-radius: 3px;
        font-weight: bold;
    }
    
    .hud-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(51, 65, 85, 0.6);
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
        backdrop-filter: blur(8px);
        box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.5);
    }
    
    .scoreboard-box {
        display: flex;
        justify-content: space-around;
        text-align: center;
        background: rgba(10, 15, 26, 0.9);
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 10px;
        margin-top: 8px;
    }
    .score-team-a {
        color: #0099FF;
        font-family: monospace;
        font-size: 1.4rem;
        font-weight: bold;
    }
    .score-team-b {
        color: #9D4EDD;
        font-family: monospace;
        font-size: 1.4rem;
        font-weight: bold;
    }
    .score-label {
        font-size: 0.72rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 59, 48, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0); }
    }
    .alert-hazard {
        background: rgba(255, 59, 48, 0.15);
        border: 1px solid #FF3B30;
        color: #FF3B30;
        padding: 10px;
        border-radius: 6px;
        font-family: monospace;
        font-weight: bold;
        animation: pulse-red 1.5s infinite;
        text-align: center;
    }
    .alert-safe {
        background: rgba(0, 255, 102, 0.10);
        border: 1px solid #00FF66;
        color: #00FF66;
        padding: 10px;
        border-radius: 6px;
        font-family: monospace;
        font-weight: bold;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Setup Session States
if "patrol_keyframes" not in st.session_state:
    st.session_state.patrol_keyframes = []

if "detector" not in st.session_state:
    models_dir = Path("models")
    best_model = models_dir / "best.pt"
    model_to_load = str(best_model) if best_model.exists() else "yolov8n.pt"
    st.session_state.detector = TacticalDetector(model_path=model_to_load, conf_threshold=0.35)

detector: TacticalDetector = st.session_state.detector

# =========================================================================
# MISSION COCKPIT SELECTOR (ROV DANAU vs DRONE SPECTATOR)
# =========================================================================
mode_selection = st.radio(
    "PILIH COCKPIT KLASIFIKASI CITRA:",
    ["🔵 ROV COCKPIT: DANAU & EKSPLORASI BAWAH AIR", "🟢 DRONE COCKPIT: SPECTATOR UDARA & DARAT"],
    horizontal=True
)

is_rov_mode = "ROV" in mode_selection
active_mode_code = "rov" if is_rov_mode else "drone"

# Status Banner Taktis
hud_accent = "#00E5FF" if is_rov_mode else "#00FF66"
vehicle_name = "ROV LAKE VISION CLASSIFIER" if is_rov_mode else "DRONE SPECTATOR RECON CLASSIFIER"
mission_objective = "DETEKSI & KLASIFIKASI CITRA OBJEK DANAU / BAWAH AIR" if is_rov_mode else "SPECTATOR TIM A VS TIM B & OBJEK DARAT"

st.markdown(f"""
<div class="tactical-header" style="border-left-color: {hud_accent};">
    <div>
        <div class="tactical-title" style="color: {hud_accent};">⚔️ {vehicle_name}</div>
        <div style="font-size: 0.8rem; color: #94A3B8; font-family: monospace;">FOKUS: {mission_objective}</div>
    </div>
    <div style="text-align: right;">
        <span class="tactical-badge" style="background: rgba(0, 229, 255, 0.15); color: {hud_accent}; border: 1px solid {hud_accent};">
            CLASSIFICATION ENGINE: ACTIVE
        </span>
        <div style="font-size: 0.75rem; color: #64748B; font-family: monospace; margin-top: 4px;">
            SYS_TIME: {datetime.now().strftime('%H:%M:%S')} // MODEL: YOLOv8n
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================================
# SIDEBAR KONTROL SENSOR AI
# =========================================================================
with st.sidebar:
    st.markdown(f"### 🎛️ INPUT STREAM ({'ROV' if is_rov_mode else 'DRONE'})")
    feed_mode = st.radio(
        "Sumber Input Visual:",
        [
            "Virtual Testbench (Simulasi Video)",
            "Screen Mirroring (Window Software)",
            "Network Stream (UDP / RTSP - ROV Link)",
            "Direct USB Webcam"
        ]
    )

    st.divider()
    st.markdown("### 🎯 PARAMETER KLASIFIKASI")
    conf_val = st.slider("Confidence Gate (Ambang Batas)", 0.10, 0.90, 0.35, 0.05)
    detector.conf_threshold = conf_val

    draw_reticle = st.toggle("Tactical HUD Reticle Crosshair", value=True)

    st.divider()
    st.markdown("### 📸 REKAMAN PATROLI (STITCHING)")
    auto_capture_keyframe = st.checkbox("Auto-Capture Keyframe tiap 2.5s", value=False)
    st.caption(f"Tersimpan: **{len(st.session_state.patrol_keyframes)} frame**")
    if st.button("🗑️ Kosongkan Buffer"):
        st.session_state.patrol_keyframes = []

# =========================================================================
# LAYOUT UTAMA: VIDEO HUD + TELEMETRI KLASIFIKASI
# =========================================================================
col_hud, col_sidebar_telemetry = st.columns([7, 3])

with col_sidebar_telemetry:
    st.markdown("#### 📊 STATUS KLASIFIKASI CITRA")

    alert_placeholder = st.empty()
    metric_total = st.empty()
    metric_hazard = st.empty()
    metric_neutral = st.empty()
    breakdown_placeholder = st.empty()
    fps_placeholder = st.empty()

with col_hud:
    stream_placeholder = st.empty()

# Inisialisasi Feed Source
stream_cap = StreamCapture()
is_active = False

video_dir = Path("testbench_samples/videos")
default_vid_name = "rov_underwater_patrol.mp4" if is_rov_mode else "drone_land_recon.mp4"

if feed_mode == "Virtual Testbench (Simulasi Video)":
    target_vid_file = video_dir / default_vid_name
    all_vids = list(video_dir.glob("*.mp4"))

    c_sel1, c_sel2 = st.columns([3, 1])
    with c_sel1:
        chosen_vid = st.selectbox(
            "Pilih Berkas Video Testbench:",
            all_vids,
            index=all_vids.index(target_vid_file) if target_vid_file in all_vids else 0,
            format_func=lambda p: p.name
        )
    with c_sel2:
        st.write("")
        st.write("")
        start_btn = st.button("▶️ ENGAGE STREAM", type="primary", use_container_width=True)

    if start_btn:
        is_active = stream_cap.open_video_file(str(chosen_vid))

elif feed_mode == "Screen Mirroring (Window Software)":
    window_titles = []
    if GW_AVAILABLE:
        window_titles = [w.title for w in gw.getAllWindows() if w.title.strip() != ""]

    if window_titles:
        w_sel1, w_sel2 = st.columns([3, 1])
        with w_sel1:
            selected_window_title = st.selectbox("Pilih Window Aplikasi Aktif:", window_titles)
        with w_sel2:
            st.write("")
            st.write("")
            start_mirror = st.button("▶️ ENGAGE MIRROR", type="primary", use_container_width=True)

        if start_mirror:
            target_win = gw.getWindowsWithTitle(selected_window_title)[0]
            if target_win:
                is_active = True
                st.session_state["mirror_win"] = target_win
    else:
        st.warning("Pustaka pygetwindow tidak mendeteksi window aktif.")

elif feed_mode == "Network Stream (UDP / RTSP - ROV Link)":
    st.markdown("##### 📡 ROV / Drone Network Video Link (UDP Protocol)")
    st.info("💡 **Catatan ROV:** Umumnya video stream ROV dikirim melalui protokol UDP H.264 (port default 5600). Pastikan port tidak diblokir firewall.")
    
    # Preset links for quick selection
    preset_cols = st.columns(3)
    preset_chosen = None
    if preset_cols[0].button("Presets: udp://@:5600 (ROV All Interfaces)", use_container_width=True):
        st.session_state["udp_input_val"] = "udp://@:5600"
    if preset_cols[1].button("Presets: udp://192.168.2.1:5600 (Companion IP)", use_container_width=True):
        st.session_state["udp_input_val"] = "udp://192.168.2.1:5600"
    if preset_cols[2].button("Presets: udp://127.0.0.1:5600 (Loopback)", use_container_width=True):
        st.session_state["udp_input_val"] = "udp://127.0.0.1:5600"

    default_udp = st.session_state.get("udp_input_val", "udp://@:5600")
    
    c_net1, c_net2 = st.columns([3, 1])
    with c_net1:
        net_stream_url = st.text_input(
            "Masukkan Network Stream Link (UDP / RTSP):",
            value=default_udp,
            placeholder="udp://@:5600 atau udp://192.168.2.1:5600"
        )
    with c_net2:
        st.write("")
        st.write("")
        start_net_btn = st.button("▶️ ENGAGE UDP STREAM", type="primary", use_container_width=True)

    if start_net_btn and net_stream_url.strip():
        with st.spinner(f"Menghubungkan ke stream {net_stream_url}..."):
            is_active = stream_cap.open_network_stream(net_stream_url.strip())
            if not is_active:
                st.error(f"❌ Gagal membuka stream dari {net_stream_url}. Pastikan ROV aktif menyiarkan paket UDP.")

elif feed_mode == "Direct USB Webcam":
    c_cam1, c_cam2 = st.columns([3, 1])
    with c_cam1:
        cam_source = st.number_input("Index Perangkat Kamera USB:", min_value=0, max_value=5, value=0, step=1)
    with c_cam2:
        st.write("")
        st.write("")
        start_cam_btn = st.button("▶️ BUKA WEBCAM", type="primary", use_container_width=True)

    if start_cam_btn:
        is_active = stream_cap.open_camera(int(cam_source))
        if not is_active:
            st.error(f"❌ Gagal mengakses kamera USB index {cam_source}.")

# =========================================================================
# STREAMING LOOP WITH PURE CLASSIFICATION TELEMETRY
# =========================================================================
if is_active:
    stop_stream_btn = st.button("⏹️ ABORT MISSION / STOP STREAM", use_container_width=True)
    prev_time = time.time()
    last_cap = time.time()
    snapshots_dir = Path("testbench_samples/patrol_snapshots")
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    while not stop_stream_btn:
        if feed_mode == "Virtual Testbench (Simulasi Video)":
            ret, frame = stream_cap.read_virtual_loop_frame()
        elif feed_mode == "Screen Mirroring (Window Software)":
            win = st.session_state.get("mirror_win")
            if win:
                frame = stream_cap.capture_screen_region(top=win.top, left=win.left, width=win.width, height=win.height)
                ret = (frame is not None)
            else:
                ret = False
        else:
            ret, frame = stream_cap.read_frame()

        if not ret or frame is None:
            break

        # Auto-Capture Keyframe
        t_now = time.time()
        if auto_capture_keyframe and (t_now - last_cap >= 2.5):
            st.session_state.patrol_keyframes.append(frame.copy())
            last_cap = t_now
            cv2.imwrite(str(snapshots_dir / f"keyframe_{int(t_now)}.jpg"), frame)

        # AI INFERENCE (MURNI IMAGE CLASSIFICATION & OBJECT DETECTION)
        results = detector.detect(
            frame,
            enable_distance=False,
            mode=active_mode_code,
            draw_hud_reticle=draw_reticle
        )
        annotated_bgr = results["annotated_frame"]

        # Hitung Latency & FPS
        curr_t = time.time()
        fps = 1.0 / (curr_t - prev_time + 1e-6)
        prev_time = curr_t

        # RENDER VIDEO KE HUD
        stream_placeholder.image(cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)

        # RENDER TELEMETRI STATUS ANCAMAN
        if results["hazard_count"] > 0:
            alert_placeholder.markdown(f"""
            <div class="alert-hazard">
                🚨 RED ALERT: {results['hazard_count']} ANCAMAN TERDETEKSI!
            </div>
            """, unsafe_allow_html=True)
        else:
            alert_placeholder.markdown(f"""
            <div class="alert-safe">
                🛡️ GREEN SECTOR: TIDAK ADA ANCAMAN
            </div>
            """, unsafe_allow_html=True)

        # METRIK MURNI KLASIFIKASI CITRA
        total_detected = len(results["detections"])
        metric_total.metric("🎯 Total Objek Terdeteksi", f"{total_detected} Objek", delta=f"Domain: {results['environment']}")
        metric_hazard.metric("🚨 Target Bahaya (Hazard)", f"{results['hazard_count']} Target", delta="Kategori Militer/Waspada")
        metric_neutral.metric("🟢 Target Netral / Aman", f"{results['neutral_count']} Objek", delta="Kategori Non-Militer")

        if is_rov_mode:
            # RINCIAN KLASIFIKASI OBJEK DANAU / BAWAH AIR
            breakdown_placeholder.markdown(f"""
            <div class="hud-card">
                <div style="font-size: 0.75rem; color: #00E5FF; font-family: monospace; font-weight: bold; margin-bottom: 6px;">
                    🐟 RINCIAN KLASIFIKASI OBJEK DANAU
                </div>
                <div style="font-size: 0.85rem; color: #E2E8F0; font-family: monospace;">
                    • Submarine/Ranjau : <b>{results['rov_stats']['submarine']}</b> unit<br/>
                    • Biota Laut/Ikan   : <b>{results['rov_stats']['marine_life']}</b> ekor<br/>
                    • Terumbu Karang   : <b>{results['rov_stats']['coral_reef']}</b> titik<br/>
                    • Friendly ROV     : <b>{results['rov_stats']['rov']}</b> unit<br/>
                    • Kapal/Perahu     : <b>{results['rov_stats']['ship']}</b> unit
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            # RINCIAN KLASIFIKASI SPECTATOR DRONE (TIM A BIRU VS TIM B UNGU)
            breakdown_placeholder.markdown(f"""
            <div class="hud-card">
                <div style="font-size: 0.75rem; color: #00FF66; font-family: monospace; font-weight: bold;">
                    ⚔️ SPECTATOR HEAD-TO-HEAD TRACKER
                </div>
                <div class="scoreboard-box">
                    <div>
                        <div class="score-team-a">{results['drone_stats']['team_a']}</div>
                        <div class="score-label">TIM A (BIRU)</div>
                    </div>
                    <div style="font-size: 1.2rem; color: #475569; align-self: center;">VS</div>
                    <div>
                        <div class="score-team-b">{results['drone_stats']['team_b']}</div>
                        <div class="score-label">TIM B (UNGU)</div>
                    </div>
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8; font-family: monospace; margin-top: 8px;">
                    • Kendaraan / Vehicle : <b>{results['drone_stats']['military_vehicle']}</b> unit<br/>
                    • Warga Sipil / Netral: <b>{results['drone_stats']['civilian']}</b> orang
                </div>
            </div>
            """, unsafe_allow_html=True)

        fps_placeholder.caption(f"Classification Engine: Online // {int(fps)} FPS // Latency: {1000.0/fps:.1f} ms")
        time.sleep(0.01)

    stream_cap.release()
