"""
Page: 3_Image_Stitching.py
Deskripsi:
    Modul Image Stitching Hybrid:
    1. Menggabungkan Citra Keyframe Hasil Patroli Live Stream ROV/Drone.
    2. Mengunggah Foto Beririsan Secara Manual.
"""

import cv2
import numpy as np
import streamlit as st
from datetime import datetime
from pathlib import Path
from PIL import Image

from core.stitcher import ImageStitcher

st.set_page_config(page_title="Image Stitching", page_icon="🗺️", layout="wide")

st.title("🗺️ Image Stitching (Panorama Jalur Patroli)")
st.caption("Menggabungkan serangkaian citra foto beririsan (overlap) dari jalur jelajah ROV / Drone")

st.info("💡 **Petunjuk Penggunaan:** Sistem mendukung penggabungan foto manual serta foto yang otomatis ditangkap dari Live Stream patroli ROV/Drone.")

col_config, col_action = st.columns([1, 2])

with col_config:
    st.subheader("⚙️ Opsi Algoritma")
    stitch_mode = st.selectbox(
        "Mode Proyeksi Stitching:",
        ["panorama", "scans"],
        format_func=lambda x: "Panorama Landscape (Kamera Berputar)" if x == "panorama" else "Planar Scan (Dasar Laut / Datar)"
    )
    crop_border = st.checkbox("Otomatis Potong Batas Hitam (Trim Borders)", value=True)

# Cek apakah ada keyframe dari live stream
session_keyframes = st.session_state.get("patrol_keyframes", [])
snapshots_dir = Path("testbench_samples/patrol_snapshots")
disk_snapshots = sorted(list(snapshots_dir.glob("*.jpg"))) if snapshots_dir.exists() else []

tab_live, tab_manual = st.tabs(["🛰️ Citra dari Live Stream Patroli", "📁 Upload Foto Manual"])

images_to_stitch = []

with tab_live:
    if session_keyframes or disk_snapshots:
        count = len(session_keyframes) if session_keyframes else len(disk_snapshots)
        st.success(f"Ditemukan **{count} frame citra patroli** dari sesi live surveillance!")

        if session_keyframes:
            images_to_stitch = session_keyframes
        else:
            images_to_stitch = [cv2.imread(str(p)) for p in disk_snapshots]

        cols = st.columns(min(len(images_to_stitch), 5))
        for idx, img in enumerate(images_to_stitch[:5]):
            with cols[idx]:
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption=f"Keyframe #{idx+1}", use_container_width=True)

        if st.button("🚀 Gabungkan Keyframe Patroli Ini", type="primary"):
            stitcher = ImageStitcher(mode=stitch_mode)
            with st.spinner("Sedang mencari fitur SIFT/ORB & homografi..."):
                success, panorama, msg = stitcher.stitch_images(images_to_stitch, crop_black_borders=crop_border)

            if success and panorama is not None:
                st.success("✅ " + msg)
                st.image(cv2.cvtColor(panorama, cv2.COLOR_BGR2RGB), caption="Hasil Panorama Jalur Patroli", use_container_width=True)

                _, enc_pano = cv2.imencode(".png", panorama)
                st.download_button(
                    label="📥 Unduh Citra Panorama (PNG)",
                    data=enc_pano.tobytes(),
                    file_name=f"live_patrol_panorama_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png"
                )
            else:
                st.error("❌ " + msg)
                st.info("Catatan: Pastikan antar keyframe memiliki overlap visual minimal 30%.")
    else:
        st.warning("Belum ada keyframe yang ditangkap dari Live Stream. Anda dapat mengaktifkan 'Auto-Capture' di halaman Live Surveillance atau mengunggah foto manual di tab sebelah.")

with tab_manual:
    uploaded_files = st.file_uploader(
        "Pilih 2 atau lebih foto jalur patroli:",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True
    )

    if uploaded_files and len(uploaded_files) >= 2:
        st.write(f"Total foto diunggah: **{len(uploaded_files)} foto**")
        manual_imgs = []
        m_cols = st.columns(min(len(uploaded_files), 5))

        for idx, f in enumerate(uploaded_files):
            f_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
            img = cv2.imdecode(f_bytes, cv2.IMREAD_COLOR)
            manual_imgs.append(img)
            with m_cols[idx % len(m_cols)]:
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption=f"Upload #{idx+1}", use_container_width=True)

        if st.button("🚀 Gabungkan Foto Manual (Stitch)", type="primary"):
            stitcher = ImageStitcher(mode=stitch_mode)
            with st.spinner("Sedang memproses stitching..."):
                success, panorama, msg = stitcher.stitch_images(manual_imgs, crop_black_borders=crop_border)

            if success and panorama is not None:
                st.success("✅ " + msg)
                st.image(cv2.cvtColor(panorama, cv2.COLOR_BGR2RGB), caption="Hasil Panorama Manual", use_container_width=True)

                _, enc_pano = cv2.imencode(".png", panorama)
                st.download_button(
                    label="📥 Unduh Citra Panorama (PNG)",
                    data=enc_pano.tobytes(),
                    file_name=f"manual_panorama_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png"
                )
            else:
                st.error("❌ " + msg)
