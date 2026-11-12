"""
Page: 2_Media_Analysis.py
Deskripsi:
    Analisis media offline (Foto & Video MP4):
    FOKUS MURNI IMAGE CLASSIFICATION & OBJECT DETECTION:
    - 🔵 Mode ROV (Danau & Bawah Air)
    - 🟢 Mode Drone (Spectator Udara & Personel Darat)
    Dilengkapi tabel deteksi taktis, confidence score, dan ekspor log CSV.
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

st.set_page_config(page_title="Media Analysis", page_icon="🎞️", layout="wide")

def render_tactical_table(df: pd.DataFrame):
    """Render tabel taktis bebas error PyArrow/NumPy."""
    html_table = df.to_html(classes="tactical-table", index=False)
    st.markdown(f"""
    <style>
        .tactical-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            margin-bottom: 15px;
            font-family: monospace;
            font-size: 0.85rem;
            color: #E2E8F0;
        }}
        .tactical-table th {{
            background-color: #1E293B;
            color: #00E5FF;
            border: 1px solid #334155;
            padding: 8px 12px;
            text-align: left;
            text-transform: uppercase;
            font-weight: bold;
        }}
        .tactical-table td {{
            border: 1px solid #1E293B;
            padding: 8px 12px;
            background-color: rgba(15, 23, 42, 0.7);
        }}
        .tactical-table tr:hover td {{
            background-color: rgba(30, 41, 59, 0.8);
        }}
    </style>
    {html_table}
    """, unsafe_allow_html=True)

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
    st.header("⚙️ Parameter Klasifikasi")
    conf_val = st.slider("Confidence Gate", 0.10, 0.90, 0.35, 0.05)
    detector.conf_threshold = conf_val

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
        results = detector.detect(img_to_process, enable_distance=False, mode=mode_code)
        annotated = results["annotated_frame"]
        detections = results["detections"]

        c1, c2 = st.columns([3, 2])
        with c1:
            st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), caption="Hasil Klasifikasi Taktis & Bounding Box", use_container_width=True)

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
            st.markdown("#### Rincian Log Klasifikasi Citra:")

            if detections:
                log_data = []
                for idx, d in enumerate(detections, 1):
                    log_data.append({
                        "No": idx,
                        "Target": d["display_name"],
                        "Confidence Score": f"{int(d['confidence'] * 100)}%",
                        "Status Ancaman": d["threat"],
                        "Keterangan": d["threat_label"],
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                df_log = pd.DataFrame(log_data)
                render_tactical_table(df_log[["Target", "Confidence Score", "Status Ancaman", "Keterangan"]])

                csv_bytes = df_log.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📊 Unduh Log Klasifikasi (CSV)",
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
                    res = detector.detect(frame, enable_distance=False, mode=mode_code)
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
                            "Threat": d["threat"]
                        })

            cap.release()
            st.success("Analisis rekaman video selesai!")

            if video_logs:
                df_vlog = pd.DataFrame(video_logs)
                render_tactical_table(df_vlog)
                st.download_button(
                    label="📥 Unduh Rekap Klasifikasi Video (CSV)",
                    data=df_vlog.to_csv(index=False).encode("utf-8"),
                    file_name=f"video_classification_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
