"""
Page: 2_Media_Analysis.py
Deskripsi:
    Analisis media offline (Foto & Video MP4):
    Mendukung Pemfilteran Mode Operasi:
    - 🔵 Mode ROV (Danau & Bawah Air)
    - 🟢 Mode Drone (Spectator Udara & Personel Darat)
    Dilengkapi tabel deteksi taktis, telemetri jarak, dan ekspor log CSV.
"""

import cv2
import tempfile
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from pathlib import Path
from PIL import Image

from core.detector import TacticalDetector
from core.distance_estimator import DistanceEstimator

st.set_page_config(page_title="Media Analysis", page_icon="🎞️", layout="wide")

st.title("🎞️ Analisis Media Visual Taktis (Foto & Video MP4)")
st.caption("Pemeriksaan Intelijen & Rekapitulasi Misi ROV Danau vs Drone Spectator")

# Load detector
if "detector" not in st.session_state:
    models_dir = Path("models")
    best_model = models_dir / "best.pt"
    model_to_load = str(best_model) if best_model.exists() else "yolov8n.pt"
    st.session_state.detector = TacticalDetector(model_path=model_to_load, conf_threshold=0.35)

detector: TacticalDetector = st.session_state.detector

# Pemilihan Mode Analisis
mode_sel = st.radio(
    "PILIH DOMAIN ANALISIS WAHANA:",
    ["🔵 Mode ROV: Danau & Bawah Air", "🟢 Mode Drone: Spectator Udara & Darat", "🌐 Mode Terpadu (Semua Target)"],
    horizontal=True
)

mode_code = "rov" if "ROV" in mode_sel else ("drone" if "Drone" in mode_sel else "all")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Parameter Analisis")
    conf_val = st.slider("Confidence Gate", 0.10, 0.90, 0.35, 0.05)
    detector.conf_threshold = conf_val

    enable_dist = st.toggle("Aktifkan Estimasi Jarak", value=True)
    camera_opt = st.selectbox(
        "Profil Optik Kamera:",
        list(DistanceEstimator.CAMERA_PROFILES.keys()),
        format_func=lambda k: DistanceEstimator.CAMERA_PROFILES[k]["name"]
    )
    detector.distance_estimator.set_camera_profile(camera_opt)

tab_img, tab_video = st.tabs(["📸 Analisis Foto Tunggal", "🎥 Analisis Rekaman Video (MP4)"])

# ----------------- TAB 1: ANALISIS FOTO TUNGGAL -----------------
with tab_img:
    st.subheader("Pilih atau Unggah Citra Misi")

    col_up, col_samples = st.columns([2, 1])
    with col_up:
        uploaded_img = st.file_uploader("Upload Foto Misi:", type=["jpg", "jpeg", "png", "webp"])

    with col_samples:
        sample_dir = Path("testbench_samples/images")
        sample_files = list(sample_dir.glob("*.*")) if sample_dir.exists() else []
        chosen_sample = None
        if sample_files:
            chosen_sample = st.selectbox("Atau Pilih Foto Sampel Uji:", ["None"] + [f.name for f in sample_files])

    img_to_process = None
    if uploaded_img is not None:
        file_bytes = np.asarray(bytearray(uploaded_img.read()), dtype=np.uint8)
        img_to_process = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    elif chosen_sample and chosen_sample != "None":
        img_to_process = cv2.imread(str(sample_dir / chosen_sample))

    if img_to_process is not None:
        results = detector.detect(img_to_process, enable_distance=enable_dist, mode=mode_code)
        annotated = results["annotated_frame"]
        detections = results["detections"]

        c1, c2 = st.columns([3, 2])
        with c1:
            st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), caption="Hasil Deteksi Taktis & Reticle HUD", use_container_width=True)

            _, encoded_png = cv2.imencode(".png", annotated)
            st.download_button(
                label="📥 Unduh Citra Beranotasi (PNG)",
                data=encoded_png.tobytes(),
                file_name=f"tactical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png"
            )

        with c2:
            st.markdown(f"### Domain Terpilih: **{results['environment']}**")
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("🚨 Target Bahaya (Hazard)", results["hazard_count"])
            m_col2.metric("🟢 Target Netral (Aman)", results["neutral_count"])

            if mode_code == "drone":
                st.info(f"⚔️ **Spectator Score:** Tim A: **{results['drone_stats']['team_a']}** | Tim B: **{results['drone_stats']['team_b']}** | Sipil: **{results['drone_stats']['civilian']}**")
            elif mode_code == "rov":
                st.info(f"🐟 **Objek Danau:** Ikan/Biota: **{results['rov_stats']['marine_life']}** | Karang: **{results['rov_stats']['coral_reef']}** | Submarine: **{results['rov_stats']['submarine']}**")

            st.divider()
            st.markdown("#### Rincian Log Target Terdeteksi:")

            if detections:
                log_data = []
                for idx, d in enumerate(detections, 1):
                    dist_str = f"{d['distance_m']} m" if d['distance_m'] is not None else "N/A"
                    log_data.append({
                        "No": idx,
                        "Target": d["display_name"],
                        "Confidence": f"{int(d['confidence'] * 100)}%",
                        "Status": d["threat"],
                        "Estimasi Jarak": dist_str,
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                df_log = pd.DataFrame(log_data)
                st.dataframe(df_log[["Target", "Confidence", "Status", "Estimasi Jarak"]], use_container_width=True)

                csv_bytes = df_log.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📊 Unduh Log Misi (CSV)",
                    data=csv_bytes,
                    file_name=f"mission_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Tidak ada target yang lolos filter mode dan threshold.")

# ----------------- TAB 2: ANALISIS VIDEO REKAMAN -----------------
with tab_video:
    st.subheader("Unggah Rekaman Video (MP4 / AVI)")
    uploaded_video = st.file_uploader("Pilih Berkas Video Rekaman Patroli:", type=["mp4", "avi", "mov"])

    if uploaded_video:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_video.read())
        video_path = tfile.name

        v_col1, v_col2 = st.columns([3, 1])
        video_placeholder = v_col1.empty()
        log_placeholder = v_col2.empty()

        if st.button("🚀 Mulai Analisis Video Taktis", type="primary"):
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            video_logs = []

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                if frame_count % 2 == 0:
                    res = detector.detect(frame, enable_distance=enable_dist, mode=mode_code)
                    annotated_v = res["annotated_frame"]

                    video_placeholder.image(
                        cv2.cvtColor(annotated_v, cv2.COLOR_BGR2RGB),
                        caption=f"Frame #{frame_count} // Mode: {mode_sel}",
                        use_container_width=True
                    )

                    for d in res["detections"]:
                        video_logs.append({
                            "Frame": frame_count,
                            "Target": d["display_name"],
                            "Confidence": f"{int(d['confidence'] * 100)}%",
                            "Threat": d["threat"],
                            "Distance": f"{d['distance_m']} m" if d['distance_m'] else "N/A"
                        })

            cap.release()
            st.success("Analisis rekaman video selesai!")

            if video_logs:
                df_vlog = pd.DataFrame(video_logs)
                st.dataframe(df_vlog, use_container_width=True)
                st.download_button(
                    label="📥 Unduh Rekap Deteksi Video (CSV)",
                    data=df_vlog.to_csv(index=False).encode("utf-8"),
                    file_name=f"video_analysis_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
