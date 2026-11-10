"""
Script: scripts/train_yolo.py
Deskripsi:
    Melatih model YOLOv8 (Transfer Learning) menggunakan dataset terpadu
    yang telah diseimbangkan di data/unified_dataset/data.yaml.

Penggunaan:
    python scripts/train_yolo.py
"""

from pathlib import Path
from ultralytics import YOLO


def train():
    base_dir = Path(__file__).resolve().parent.parent
    data_yaml = base_dir / "data" / "unified_dataset" / "data.yaml"
    models_dir = base_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    if not data_yaml.exists():
        print(f"Error: {data_yaml} tidak ditemukan!")
        return

    print("==========================================================")
    print("MEMULAI TRAINING YOLOv8 (TRANSFER LEARNING)")
    print(f"Dataset YAML: {data_yaml}")
    print("==========================================================")

    # Menggunakan pre-trained YOLOv8 Nano (cepat, ringan & akurat)
    model = YOLO("yolov8n.pt")

    # Hyperparameter yang dioptimalkan untuk workshop
    results = model.train(
        data=str(data_yaml),
        epochs=35,            # 35 epochs cukup untuk konvergensi transfer learning
        imgsz=640,
        batch=16,             # Turunkan ke 8 jika memori GPU kecil
        patience=8,           # Early stopping jika tidak membaik dalam 8 epoch
        save=True,
        project=str(models_dir),
        name="tactical_yolo_run",
        exist_ok=True,
        verbose=True
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

