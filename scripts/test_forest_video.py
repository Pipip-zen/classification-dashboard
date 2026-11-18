import sys
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

import cv2
from core.detector import TacticalDetector

video_path = Path("testbench_samples/videos/drone_forest_person_patrol.mp4")
detector = TacticalDetector(model_path="models/best.pt", conf_threshold=0.20)

cap = cv2.VideoCapture(str(video_path))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

detected_classes = set()
frame_idx = 0
person_detections = 0
tree_detections = 0

# Sample every 30 frames (~1 sec)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    if frame_idx % 30 == 0:
        res = detector.detect(frame, mode="drone", enable_dusk=False)
        for d in res["detections"]:
            cls_name = d["class_name"]
            detected_classes.add(cls_name)
            if cls_name in ["civilian", "soldier"]:
                person_detections += 1
            elif cls_name == "tree":
                tree_detections += 1

cap.release()

print("==================================================")
print("HASIL UJI COBA FOOTAGE DRONE HUTAN (FOREST + PERSON)")
print(f"Total Frame Diuji   : {frame_idx} frame (~{frame_idx/24:.1f} detik)")
print(f"Kelas Terdeteksi    : {detected_classes}")
print(f"Deteksi Manusia     : {person_detections} kali")
print(f"Deteksi Pohon/Hutan : {tree_detections} kali")
print("==================================================")
