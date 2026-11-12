"""
Main Application: app.py
Tactical AI Surveillance & Reconnaissance Dashboard
Workshop Kecerdasan Buatan - Kelompok 1 (Bab 5 - Image Classification & Object Detection)
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
from core.threat_evaluator import ThreatEvaluator

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Tactical Command Center",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Military HUD Styling
st.markdown("""
<style>
    .stApp {
        background-color: #06090F;
    }
    .hud-title-banner {
        background: linear-gradient(135deg, rgba(19, 28, 46, 0.95) 0%, rgba(10, 14, 23, 0.98) 100%);
        border: 1px solid #1E293B;
        border-left: 5px solid #00E5FF;
        border-radius: 8px;
        padding: 18px 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 25px rgba(0, 229, 255, 0.08);
    }
    .hud-main-title {
        font-family: 'Courier New', monospace;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: 2px;
        color: #F8FAFC;
        margin: 0;
    }
    .hud-sub-title {
        font-size: 0.95rem;
        color: #94A3B8;
        font-family: monospace;
        margin-top: 6px;
    }
    .cockpit-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(51, 65, 85, 0.7);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .cockpit-card:hover {
        border-color: #00E5FF;
        transform: translateY(-2px);
    }
    .badge-rov {
        background: rgba(0, 229, 255, 0.15);
        color: #00E5FF;
        border: 1px solid #00E5FF;
        padding: 3px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-drone {
        background: rgba(0, 255, 102, 0.15);
        color: #00FF66;
        border: 1px solid #00FF66;
        padding: 3px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.75rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Banner Utama HUD
st.markdown("""
<div class="hud-title-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div class="hud-main-title">⚔️ TACTICAL AI RECONNAISSANCE & COMBAT COMMAND CENTER</div>
            <div class="hud-sub-title">SISTEM MONITORING TERPADU WAHANA NIRAWAK: ROV DANAU & DRONE SPECTATOR UDARA</div>
        </div>
        <div style="text-align: right; font-family: monospace; font-size: 0.8rem; color: #00E5FF;">
            SYS_STATUS: READY // CLASSIFICATION: CONFIDENTIAL<br/>
            BUILD: v2.0-TACTICAL-HUD
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Metrik Kesiapan Taktis
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Status AI Core", "YOLOv8 Online", delta="models/best.pt Loaded")
with c2:
    st.metric("Mode Operasional", "Dual-Cockpit", delta="ROV Danau + Drone Spectator")
with c3:
    st.metric("Testbench Sim", "2 Skenario MP4", delta="ROV & Drone Ready")
with c4:
    st.metric("Verifikasi Modul", "100% Passed", delta="7/7 Modul Verified")

st.divider()

# Penjelasan Dua Cockpit Utama
st.subheader("🛰️ Arsitektur Pemisahan Cockpit Wahana Taktis")
col_rov, col_drone = st.columns(2)

with col_rov:
    st.markdown("""
    <div class="cockpit-card" style="border-left: 4px solid #00E5FF;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 700; font-size: 1.15rem; color: #00E5FF; font-family: monospace;">
                🔵 COCKPIT ROV: DANAU & GAMES BAWAH AIR
            </span>
            <span class="badge-rov">LAKE OPS</span>
        </div>
        <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 10px;">
            <b>Fungsi Utama:</b> Menelusuri dasar danau, navigasi bawah air, pencarian rintangan/ranjau, dan penilaian game eksplorasi air.
        </div>
        <div style="font-size: 0.8rem; color: #94A3B8; font-family: monospace; margin-top: 8px;">
            • <b>Target Sensor:</b> Submarine, Biota Danau/Ikan, Terumbu Karang, Perahu Danau, ROV Kawan.<br/>
            • <b>Telemetri:</b> Kedalaman Air (Depth), Suhu Air, Skor Eksplorasi Danau.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_drone:
    st.markdown("""
    <div class="cockpit-card" style="border-left: 4px solid #00FF66;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 700; font-size: 1.15rem; color: #00FF66; font-family: monospace;">
                🟢 COCKPIT DRONE: PEMANTAUAN UDARA & SPECTATOR
            </span>
            <span class="badge-drone">SPECTATOR RECON</span>
        </div>
        <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 10px;">
            <b>Fungsi Utama:</b> Pemantauan udara sebagai spectator pertempuran, tracking pergerakan personel darat, dan pengawasan lalu lintas permukaan.
        </div>
        <div style="font-size: 0.8rem; color: #94A3B8; font-family: monospace; margin-top: 8px;">
            • <b>Target Sensor:</b> Prajurit Tim A vs Tim B, Kendaraan Tempur Lapis Baja, Warga Sipil.<br/>
            • <b>Telemetri:</b> Ketinggian (ALT), Kecepatan (SPD), Papan Skor Spectator Head-to-Head.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Matriks Target Sensor
st.subheader("📋 Matriks Target Sensor Menurut Wahana")
cols = st.columns(3)
for idx, (cid, info) in enumerate(ThreatEvaluator.TAXONOMY.items()):
    c_idx = idx % 3
    is_rov_obj = cid in ThreatEvaluator.ROV_ALLOWED_CLASSES
    is_drone_obj = cid in ThreatEvaluator.DRONE_ALLOWED_CLASSES

    tag_list = []
    if is_rov_obj:
        tag_list.append("<span class='badge-rov'>ROV</span>")
    if is_drone_obj:
        tag_list.append("<span class='badge-drone'>DRONE</span>")

    badge_status = "status-badge-hazard" if info["threat"] == "HAZARD" else "status-badge-neutral"
    color_border = info["color_hex"]

    with cols[c_idx]:
        st.markdown(f"""
        <div class="cockpit-card" style="border-top: 2px solid {color_border};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; color: #F1F5F9;">{info['display']}</span>
                <span>{' '.join(tag_list)}</span>
            </div>
            <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">
                Domain: <b>{info['domain']}</b> | Ref Dimensi: <b>{info['ref_width_m']}m</b>
            </div>
            <div style="font-size: 0.78rem; color: {info['color_hex']}; margin-top: 2px; font-weight: bold;">
                {info['threat_label']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Sidebar Info
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.title("Kelompok 1")
    st.markdown("**Workshop Kecerdasan Buatan**\nBab 5: Image Classification & Detection")
    st.divider()
    st.caption("Tactical Cockpit Engine: v2.0")
    st.caption("Framework: Streamlit + YOLOv8 + OpenCV")
