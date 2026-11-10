"""
Main Application: app.py
Tactical AI Surveillance & Reconnaissance Dashboard
Workshop Kecerdasan Buatan - Kelompok 1 (Bab 5 - Image Classification & Object Detection)
"""

import streamlit as st
from pathlib import Path
from core.threat_evaluator import ThreatEvaluator

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Tactical AI Surveillance Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Tactical Theme)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #9E9E9E;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #1E232A;
        border: 1px solid #2D3748;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .status-badge-hazard {
        background-color: rgba(255, 59, 48, 0.2);
        color: #FF3B30;
        border: 1px solid #FF3B30;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .status-badge-neutral {
        background-color: rgba(52, 199, 89, 0.2);
        color: #34C759;
        border: 1px solid #34C759;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Header Utama
st.markdown('<div class="main-title">🛡️ TACTICAL AI SURVEILLANCE DASHBOARD</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Sistem Klasifikasi Multimodal ROV & Drone Bawah Air / Darat (Militer vs Sipil)</div>', unsafe_allow_html=True)

# Overview Status Sistem
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Status Model AI", value="YOLOv8 Ready", delta="Transfer Learning")

with col2:
    st.metric(label="Dataset Terpadu", value="2.660 Train", delta="352 Validasi")

with col3:
    st.metric(label="Domain Cakupan", value="3 Domain", delta="Land, Surface, Underwater")

with col4:
    st.metric(label="Taksonomi Kelas", value="9 Target", delta="Militer & Sipil")

st.divider()

# Grid Taksonomi & Status Ancaman
st.subheader("📋 Matriks Taksonomi & Evaluasi Ancaman (Threat Matrix)")

cols = st.columns(3)
for idx, (cid, info) in enumerate(ThreatEvaluator.TAXONOMY.items()):
    col_idx = idx % 3
    with cols[col_idx]:
        badge_class = "status-badge-hazard" if info["threat"] == "HAZARD" else "status-badge-neutral"
        st.markdown(f"""
        <div class="metric-card" style="margin-bottom: 12px; text-align: left;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; font-size: 1.05rem;">{info['display']}</span>
                <span class="{badge_class}">{info['threat']}</span>
            </div>
            <div style="font-size: 0.85rem; color: #8E8E93; margin-top: 6px;">
                Domain: <b>{info['domain']}</b> | Ref Dimensi: <b>{info['ref_width_m']}m</b>
            </div>
            <div style="font-size: 0.8rem; color: {info['color_hex']}; margin-top: 4px;">
                {info['threat_label']}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# Panduan Alur Kerja Dashboard
st.subheader("🧭 Panduan Modul Navigasi")
nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    st.info("### 🛰️ 1. Live Surveillance\n"
            "- **Screen Mirroring Window:** Menangkap live feed window controller ROV / Drone.\n"
            "- **Virtual Testbench:** Pemutaran video rekaman offline untuk simulasi uji mingguan.")

with nav_col2:
    st.info("### 🎞️ 2. Media Analysis\n"
            "- **Upload Video MP4:** Analisis video rekaman misi per-frame.\n"
            "- **Upload Foto Tunggal:** Deteksi instan, telemetri jarak, dan download log CSV.")

with nav_col3:
    st.info("### 🛠️ 3 & 4. Utilitas CV\n"
            "- **Image Stitching:** Menggabungkan foto jalur patroli menjadi panorama.\n"
            "- **Image Inpainting:** Menghapus koordinat OSD sensitif / sensor noise.")

# Sidebar Informasi Tim
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.title("Kelompok 1")
    st.markdown("**Workshop Kecerdasan Buatan**\nBab 5: Image Classification & Detection")
    st.divider()
    st.caption("Status Sistem: Operational")
    st.caption("Framework: Streamlit + YOLOv8 + OpenCV")

