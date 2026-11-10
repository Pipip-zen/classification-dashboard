"""
Page: 3_Image_Stitching.py
Deskripsi:
    Modul Image Stitching untuk menggabungkan serangkaian foto beririsan
    dari jalur patroli ROV/Drone menjadi satu citra panorama beresolusi penuh.
"""

import cv2
import numpy as np
import streamlit as st
from datetime import datetime
from PIL import Image

from core.stitcher import ImageStitcher

st.set_page_config(page_title="Image Stitching", page_icon="🗺️", layout="wide")

st.title("🗺️ Image Stitching (Panorama Jalur Patroli)")
st.caption("Menggabungkan serangkaian citra foto beririsan (overlap) dari jalur jelajah ROV / Drone")

st.info("💡 **Petunjuk Penggunaan:** Unggah minimal 2 foto yang diambil berurutan dengan area bertampalan (*overlap*) minimal 30% untuk menghasilkan panorama yang mulus.")

col_config, col_action = st.columns([1, 2])

with col_config:
    stitch_mode = st.selectbox(
        "Mode Proyeksi Stitching:",
        ["panorama", "scans"],
        format_func=lambda x: "Panorama Landscape (Kamera Berputar)" if x == "panorama" else "Planar Scan (Kamera Bergerak Datar/Dasar Laut)"
    )
    crop_border = st.checkbox("Otomatis Potong Batas Hitam (Trim Borders)", value=True)

uploaded_files = st.file_uploader(
    "Pilih 2 atau lebih foto jalur patroli:",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True
)

if uploaded_files and len(uploaded_files) >= 2:
    st.write(f"Total foto diunggah: **{len(uploaded_files)} foto**")

    # Tampilkan thumbnail foto-foto yang diunggah
    cols = st.columns(min(len(uploaded_files), 5))
    images_bgr = []

    for idx, f in enumerate(uploaded_files):
        f_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
        img = cv2.imdecode(f_bytes, cv2.IMREAD_COLOR)
        images_bgr.append(img)

        with cols[idx % len(cols)]:
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption=f"Frame #{idx+1}", use_container_width=True)

    st.divider()

    if st.button("🚀 Mulai Gabungkan Foto (Stitch Panorama)", type="primary"):
        stitcher = ImageStitcher(mode=stitch_mode)
        with st.spinner("Sedang mencari titik fitur (keypoints) & menghitung homografi..."):
            success, panorama, msg = stitcher.stitch_images(images_bgr, crop_black_borders=crop_border)

        if success and panorama is not None:
            st.success("✅ " + msg)
            st.image(cv2.cvtColor(panorama, cv2.COLOR_BGR2RGB), caption="Hasil Citra Panorama Jalur Patroli", use_container_width=True)

            _, enc_pano = cv2.imencode(".png", panorama)
            st.download_button(
                label="📥 Unduh Citra Panorama (PNG)",
                data=enc_pano.tobytes(),
                file_name=f"patrol_panorama_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png"
            )
        else:
            st.error("❌ " + msg)
            st.warning("Tips: Pastikan kamera bergerak dengan orientasi searah dan terdapat tekstur/fitur visual yang cukup pada area tumpang tindih.")
elif uploaded_files and len(uploaded_files) < 2:
    st.warning("Silakan unggah minimal 2 foto.")

