"""
Page: 4_Image_Inpainting.py
Deskripsi:
    Modul Image Inpainting untuk membersihkan noise visual, artefak kamera (gelembung/debu),
    atau menyensor koordinat sensitif OSD sebelum laporan intelijen dibagikan.
"""

import cv2
import numpy as np
import streamlit as st
from datetime import datetime
from PIL import Image

from core.inpainter import ImageInpainter

st.set_page_config(page_title="Image Inpainting", page_icon="🧹", layout="wide")

st.title("🧹 Image Inpainting (Sanitasi Noise & Sensor Koordinat)")
st.caption("Menghilangkan teks OSD sensitif (GPS, baterai, timestamp) dan artefak optik kamera")

st.info("💡 **Alur Kerja:** Unggah citra patroli, tentukan koordinat kotak yang ingin disensor (atau klik tombol cepat Preset Sudut OSD), lalu sistem akan merekonstruksi area tersebut secara mulus.")

uploaded_img = st.file_uploader("Pilih Citra yang Ingin Dibersihkan:", type=["jpg", "jpeg", "png", "webp"])

if uploaded_img is not None:
    f_bytes = np.asarray(bytearray(uploaded_img.read()), dtype=np.uint8)
    orig_bgr = cv2.imdecode(f_bytes, cv2.IMREAD_COLOR)
    h, w = orig_bgr.shape[:2]

    col_preview, col_controls = st.columns([2, 1])

    with col_controls:
        st.subheader("⚙️ Pengaturan Inpainting")

        method = st.radio(
            "Algoritma Rekonstruksi:",
            ["telea", "ns"],
            format_func=lambda x: "Fast Marching (Telea - Halus)" if x == "telea" else "Fluid Dynamics (Navier-Stokes - Gradien Air)"
        )
        radius = st.slider("Radius Rekonstruksi (Inpaint Radius)", 1, 15, 3)

        st.divider()
        st.subheader("📍 Pemilihan Area Masker")

        # Tombol Cepat Preset OSD
        st.markdown("**Tombol Cepat Preset Sudut OSD:**")
        p_c1, p_c2 = st.columns(2)
        preset_action = None
        if p_c1.button("📌 Kiri Atas (GPS)"):
            preset_action = "top_left"
        if p_c2.button("⏱️ Kanan Bawah (Time)"):
            preset_action = "bottom_right"

        # Slider Koordinat Kotak Sensor
        def_x = 20 if preset_action != "bottom_right" else max(0, w - 250)
        def_y = 20 if preset_action != "bottom_right" else max(0, h - 80)
        def_w = 220
        def_h = 50

        box_x = st.slider("Posisi X (Piksel)", 0, w, def_x, 5)
        box_y = st.slider("Posisi Y (Piksel)", 0, h, def_y, 5)
        box_w = st.slider("Lebar Kotak (Width)", 10, w, def_w, 5)
        box_h = st.slider("Tinggi Kotak (Height)", 10, h, def_h, 5)

        # Buat Masker
        boxes_to_inpaint = [(box_x, box_y, box_x + box_w, box_y + box_h)]
        mask = ImageInpainter.create_box_mask((h, w), boxes_to_inpaint)

        # Preview kotak pada gambar
        preview_box_img = orig_bgr.copy()
        cv2.rectangle(preview_box_img, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 255), 2)

    with col_preview:
        st.subheader("Preview Area yang Akan Disensor")
        st.image(cv2.cvtColor(preview_box_img, cv2.COLOR_BGR2RGB), caption="Kotak Merah = Area yang Akan Di-inpaint", use_container_width=True)

    st.divider()

    if st.button("✨ Jalankan Inpainting Sekarang", type="primary"):
        inpainter = ImageInpainter(method=method, radius=radius)
        with st.spinner("Sedang merekonstruksi piksel citra..."):
            result_bgr = inpainter.inpaint(orig_bgr, mask)

        st.success("✅ Inpainting berhasil! Area sensitif telah disensor secara mulus.")

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.image(cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB), caption="Sebelum Inpainting (Original)", use_container_width=True)
        with res_col2:
            st.image(cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB), caption="Sesudah Inpainting (Sanitized)", use_container_width=True)

        _, enc_res = cv2.imencode(".png", result_bgr)
        st.download_button(
            label="📥 Unduh Citra Bersih (PNG)",
            data=enc_res.tobytes(),
            file_name=f"sanitized_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            mime="image/png"
        )

