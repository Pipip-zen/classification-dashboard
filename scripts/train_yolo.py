"""
Script: scripts/train_yolo.py
Deskripsi:
    Melatih model YOLOv8 (Transfer Learning) menggunakan dataset terpadu
    yang telah diseimbangkan di data/unified_dataset/data.yaml.

Penggunaan:
    python scripts/train_yolo.py
"""

from pathlib import Path
import torch
from ultralytics import YOLO


def train():
    base_dir = Path(__file__).resolve().parent.parent
    data_yaml = base_dir / "data" / "unified_dataset" / "data.yaml"
    models_dir = base_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    if not data_yaml.exists():
        print(f"Error: {data_yaml} tidak ditemukan!")
        return

    device = 0 if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"

    print("==========================================================")
    print("MEMULAI TRAINING YOLOv8 (GPU ACCELERATED TRANSFER LEARNING)")
    print(f"Device       : {device} ({device_name})")
    print(f"Dataset YAML : {data_yaml}")
    print("==========================================================")

    target_best = models_dir / "best.pt"
    model_to_start = str(target_best) if target_best.exists() else "yolov8n.pt"
    print(f"Base Weights : {model_to_start}")
    model = YOLO(model_to_start)

    # Hyperparameter yang dioptimalkan untuk GPU RTX A2000 (4GB VRAM)
    results = model.train(
        data=str(data_yaml),
        epochs=15,            # 15 epochs fine-tuning pada GPU (~3-4 menit)
        imgsz=640,            # Resolusi tajam 640x640 untuk detail taktis
        batch=16,             # Pas untuk 4GB VRAM YOLOv8n
        workers=2,            # Stabil pada OS Windows
        device=device,
        patience=8,           # Early stopping jika tidak membaik dalam 8 epoch
        save=True,
        project=str(models_dir),
        name="tactical_yolo_run",
        exist_ok=True,
        verbose=True,
        hsv_h=0.015,          # Augmentasi hue spektrum air
        hsv_s=0.6,            # Augmentasi saturasi
        hsv_v=0.4,            # Augmentasi kecerahan air
        fliplr=0.5            # Flip horizontal fauna & karang
    )

    # Simpan bobot terbaik ke models/best.pt
    best_weight = models_dir / "tactical_yolo_run" / "weights" / "best.pt"
    target_best = models_dir / "best.pt"
    if best_weight.exists():
        import shutil
        shutil.copy2(best_weight, target_best)
        print(f"\n[SUKSES] Bobot model terbaik disimpan di: {target_best}")
    else:
        print("\nTraining selesai.")


if __name__ == "__main__":
    train()

