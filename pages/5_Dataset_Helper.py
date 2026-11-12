"""
Page: 5_Dataset_Helper.py
Deskripsi:
    Pusat pemantauan dataset terpadu (data/unified_dataset/)
    dan kontrol pelatihan model transfer learning YOLOv8.
"""

import yaml
import pandas as pd
import streamlit as st
from pathlib import Path
from PIL import Image

st.set_page_config(page_title="Dataset Helper", page_icon="📦", layout="wide")

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

st.title("📦 Pusat Manajemen Dataset & Training AI")
st.caption("Pemeriksaan visual data terpadu hasil penggabungan 6 dataset Roboflow")

unified_dir = Path("data/unified_dataset")
yaml_path = unified_dir / "data.yaml"

if not yaml_path.exists():
    st.error("Dataset terpadu belum ditemukan di `data/unified_dataset/data.yaml`.")
    st.stop()

with open(yaml_path, "r", encoding="utf-8") as f:
    yaml_config = yaml.safe_load(f)

classes = yaml_config.get("names", {})

# Hitung statistik gambar riil di folder
splits = ["train", "valid", "test"]
stats = {s: len(list((unified_dir / s / "images").glob("*.*"))) for s in splits}

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Train Set", f"{stats['train']} gambar")
col2.metric("Total Valid Set", f"{stats['valid']} gambar")
col3.metric("Total Test Set", f"{stats['test']} gambar")
col4.metric("Jumlah Kelas", f"{len(classes)} kelas")

st.divider()

# Tab Tampilan Data & Pelatihan
tab_dist, tab_inspect, tab_train = st.tabs(["📊 Distribusi & Konfigurasi", "🔍 Inspeksi Gambar per Kelas", "🚀 Jalankan Pelatihan (Training)"])

with tab_dist:
    st.subheader("Konfigurasi Taksonomi data.yaml")
    df_classes = pd.DataFrame([
        {"Class ID": cid, "Nama Kelas": name} for cid, name in classes.items()
    ])
    render_tactical_table(df_classes)

with tab_inspect:
    st.subheader("Lihat Contoh Sampel Gambar dari Dataset Terpadu")
    sel_split = st.selectbox("Pilih Split:", ["train", "valid", "test"])
    img_folder = unified_dir / sel_split / "images"
    all_imgs = list(img_folder.glob("*.*"))

    if all_imgs:
        st.write(f"Menampilkan 8 sampel acak dari {sel_split}:")
        sample_display = all_imgs[:8]
        cols = st.columns(4)
        for idx, img_p in enumerate(sample_display):
            with cols[idx % 4]:
                st.image(Image.open(img_p), caption=img_p.name, use_container_width=True)
    else:
        st.warning(f"Belum ada gambar di folder {sel_split}.")

with tab_train:
    st.subheader("Pelatihan Model YOLOv8 (Transfer Learning)")
    st.info("💡 Model dilatih menggunakan bobot dasar pre-trained `yolov8n.pt` dan disesuaikan ke 9 kelas taksonomi terpadu.")

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        epochs = st.slider("Jumlah Epochs:", 10, 100, 35, 5)
        batch = st.select_slider("Batch Size:", [4, 8, 16, 32], value=16)

    with t_col2:
        imgsz = st.select_slider("Image Resolution (px):", [320, 416, 640], value=640)
        patience = st.slider("Early Stopping Patience:", 3, 15, 8)

    st.markdown("**Perintah Terminal untuk Menjalankan Training:**")
    st.code(f"python scripts/train_yolo.py", language="bash")

    models_dir = Path("models")
    best_pt = models_dir / "best.pt"
    if best_pt.exists():
        st.success(f"✅ Bobot model terbaik (`best.pt`) sudah tersedia di folder `models/`!")
    else:
        st.warning("Bobot `models/best.pt` belum terbentuk. Jalankan `python scripts/train_yolo.py` di terminal untuk memulai proses training.")
