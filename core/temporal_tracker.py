"""
Module: core/temporal_tracker.py
Deskripsi:
    Temporal IoU Tracker & Class Smoothing Engine:
    Mencegah flickering / loncatan kelas antar-frame (misal: civilian tiba-tiba terbaca soldier lalu civilian lagi).
    Menjaga identitas objek yang dilacak dan menerapkan filter konsistensi temporal (Majority Voting & EMA Confidence).
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


def calculate_iou(box1: List[int], box2: List[int]) -> float:
    """Menghitung IoU (Intersection over Union) antara dua box [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = max(1, (box1[2] - box1[0]) * (box1[3] - box1[1]))
    area2 = max(1, (box2[2] - box2[0]) * (box2[3] - box2[1]))
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return float(inter_area) / float(union_area)


class TrackedTarget:
    def __init__(self, track_id: int, initial_box: List[int], initial_class: int, initial_conf: float):
        self.track_id = track_id
        self.box = initial_box
        self.current_class = initial_class
        self.current_conf = initial_conf
        
        # Riwayat kelas untuk smoothing
        self.class_history: List[int] = [initial_class]
        self.conf_history: List[float] = [initial_conf]
        self.frames_since_update = 0
        self.total_seen = 1

    def update(self, box: List[int], cls_id: int, conf: float, max_history: int = 10):
        # Update koordinat dengan perataan halus (smooth box)
        alpha = 0.7
        self.box = [
            int(alpha * box[0] + (1 - alpha) * self.box[0]),
            int(alpha * box[1] + (1 - alpha) * self.box[1]),
            int(alpha * box[2] + (1 - alpha) * self.box[2]),
            int(alpha * box[3] + (1 - alpha) * self.box[3])
        ]
        
        self.class_history.append(cls_id)
        if len(self.class_history) > max_history:
            self.class_history.pop(0)

        self.conf_history.append(conf)
        if len(self.conf_history) > max_history:
            self.conf_history.pop(0)

        # Majority voting untuk kelas manusia (0: soldier vs 2: civilian)
        # Menolak fluktuasi 1 frame sporadis
        human_classes = {0, 2}
        if cls_id in human_classes:
            recent_humans = [c for c in self.class_history if c in human_classes]
            if recent_humans:
                soldier_votes = recent_humans.count(0)
                civilian_votes = recent_humans.count(2)
                # Butuh minimal 60% suara untuk beralih kelas manusia
                if soldier_votes > civilian_votes and (soldier_votes / len(recent_humans)) >= 0.6:
                    self.current_class = 0
                elif civilian_votes > soldier_votes and (civilian_votes / len(recent_humans)) >= 0.6:
                    self.current_class = 2
                else:
                    self.current_class = self.class_history[-1]
        else:
            self.current_class = cls_id

        self.current_conf = float(np.mean(self.conf_history))
        self.frames_since_update = 0
        self.total_seen += 1


class TemporalTracker:
    def __init__(self, iou_threshold: float = 0.35, max_age: int = 15):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.next_id = 1
        self.tracks: Dict[int, TrackedTarget] = {}

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mencocokkan deteksi frame baru dengan jejak objek sebelumnya menggunakan IoU matching.
        Menstabilkan kelas yang rentan fluktuasi (prajurit vs sipil).
        """
        matched_track_ids = set()
        matched_det_indices = set()

        # 1. Matching via Matriks IoU Greedy
        if self.tracks and detections:
            track_ids = list(self.tracks.keys())
            
            for t_id in track_ids:
                track = self.tracks[t_id]
                best_iou = 0.0
                best_det_idx = -1

                for idx, det in enumerate(detections):
                    if idx in matched_det_indices:
                        continue
                    box = det.get("box", det.get("bbox", [0, 0, 0, 0]))
                    iou = calculate_iou(track.box, box)
                    if iou > best_iou:
                        best_iou = iou
                        best_det_idx = idx

                if best_iou >= self.iou_threshold and best_det_idx >= 0:
                    det = detections[best_det_idx]
                    box = det.get("box", det.get("bbox", [0, 0, 0, 0]))
                    cls_id = det.get("class_id", 0)
                    conf = det.get("confidence", 0.0)

                    track.update(box, cls_id, conf)
                    matched_track_ids.add(t_id)
                    matched_det_indices.add(best_det_idx)

                    # Update deteksi dengan kelas stabil dari tracker
                    det["track_id"] = t_id
                    det["class_id"] = track.current_class
                    det["confidence"] = track.current_conf

        # 2. Tambahkan Jejak Baru untuk Deteksi yang Tidak Cocok
        for idx, det in enumerate(detections):
            if idx not in matched_det_indices:
                box = det.get("box", det.get("bbox", [0, 0, 0, 0]))
                cls_id = det.get("class_id", 0)
                conf = det.get("confidence", 0.0)

                new_track = TrackedTarget(self.next_id, box, cls_id, conf)
                self.tracks[self.next_id] = new_track
                det["track_id"] = self.next_id
                self.next_id += 1

        # 3. Increment umur jejak yang tidak terdeteksi & bersihkan jejak usang
        dead_ids = []
        for t_id, track in self.tracks.items():
            if t_id not in matched_track_ids:
                track.frames_since_update += 1
                if track.frames_since_update > self.max_age:
                    dead_ids.append(t_id)

        for d_id in dead_ids:
            del self.tracks[d_id]

        return detections
