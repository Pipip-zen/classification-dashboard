import sys
import cv2
import json
from pathlib import Path

# Add project root to sys.path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.detector import TacticalDetector

img_path = Path("testbench_samples/images/drone_urban_street.jpg")
if not img_path.exists():
    print(f"Error: {img_path} not found")
    exit(1)

detector = TacticalDetector(model_path="models/best.pt", conf_threshold=0.20)
img = cv2.imread(str(img_path))
res = detector.detect(img, enable_distance=True, mode="drone")

print("=== HASIL DETEKSI DRONE SPECTATOR ===")
print("Total objek terdeteksi:", len(res["detections"]))
for i, d in enumerate(res["detections"]):
    print(f"{i+1}. Kelas: {d['class_name']} (ID: {d['class_id']}), Conf: {d['confidence']:.2f}, Box: {d['box']}, Jarak: {d.get('distance_m')} m, Subtipe: {d.get('subtype')}")

print("\n=== PENGUJIAN AMBANG BATAS CONFIDENCE ===")
for c in [0.35, 0.30, 0.25, 0.20, 0.15]:
    det = TacticalDetector(model_path="models/best.pt", conf_threshold=c)
    res_c = det.detect(img, enable_distance=False, mode="drone")
    names = [f"{d['display_name']} ({d['confidence']:.2f})" for d in res_c["detections"]]
    print(f"Conf {c:.2f} -> {len(res_c['detections'])} Objek: {names}")


# Simpan citra teranotasi untuk inspeksi
out_path = Path("testbench_samples/images/drone_urban_street_annotated.jpg")
cv2.imwrite(str(out_path), res["annotated_frame"])
print(f"\nCitra teranotasi berhasil disimpan di: {out_path}")
