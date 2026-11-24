"""
Module: server/state.py
Deskripsi:
    Global state container untuk FastAPI backend:
    - AI Model (TacticalDetector)
    - Taktis Evaluator & Distance Estimator
    - Parameter HUD & Cockpit Mode
    - WebSocket Telemetry Broadcaster
"""

import threading
from typing import Dict, Any, Optional, Set
from fastapi import WebSocket
from pathlib import Path

from core.detector import TacticalDetector
from core.threat_evaluator import ThreatEvaluator
from core.distance_estimator import DistanceEstimator
from core.orientation_estimator import OrientationEstimator


class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Inisialisasi Core Engine
        base_dir = Path(__file__).resolve().parent.parent
        model_path = base_dir / "models" / "best.pt"
        if not model_path.exists():
            model_path = base_dir / "models" / "yolov8n.pt"
            
        self.model_path = str(model_path)
        self.detector = TacticalDetector(self.model_path)
        self.threat_evaluator = ThreatEvaluator()
        self.distance_estimator = DistanceEstimator()
        self.orientation_estimator = OrientationEstimator()
        
        # State Operasional
        self.cockpit_mode: str = "drone"  # 'drone' | 'rov'
        self.confidence_gate: float = 0.25
        self.dusk_enhancer: bool = False
        self.reticle_visible: bool = True
        self.labels_visible: bool = True
        self.compact_hud: bool = False
        
        # Status Streaming
        self.stream_active: bool = False
        self.source_type: str = "testbench"  # 'testbench', 'youtube', 'screen', 'network', 'webcam', 'tiktok'
        self.source_param: str = "drone_forest_person_patrol.mp4"
        self.current_fps: float = 0.0
        self.last_latency_ms: float = 0.0
        
        # Telemetri Terakhir (Cache)
        self.latest_telemetry: Dict[str, Any] = {
            "cockpit_mode": self.cockpit_mode,
            "threat_level": "GREEN SECTOR",
            "threat_color_hex": "#00FF66",
            "total_objects": 0,
            "hazard_count": 0,
            "neutral_count": 0,
            "fps": 0.0,
            "latency_ms": 0.0,
            "heading_deg": 0.0,
            "cardinal": "N",
            "turn_rate_dps": 0.0,
            "compass_calibrated": False,
            "detections": []
        }
        
        # WebSocket Clients
        self.active_websockets: Set[WebSocket] = set()
        self.ws_lock = threading.Lock()

    def update_config(self, **kwargs):
        with self.lock:
            for k, v in kwargs.items():
                if hasattr(self, k) and v is not None:
                    setattr(self, k, v)
            if "cockpit_mode" in kwargs:
                self.latest_telemetry["cockpit_mode"] = self.cockpit_mode

    def reload_detector(self) -> bool:
        with self.lock:
            try:
                self.detector = TacticalDetector(self.model_path)
                return True
            except Exception as e:
                print(f"[ERROR] Gagal memuat ulang detector: {e}")
                return False

    async def register_ws(self, ws: WebSocket):
        with self.ws_lock:
            self.active_websockets.add(ws)

    def unregister_ws(self, ws: WebSocket):
        with self.ws_lock:
            self.active_websockets.discard(ws)

    async def broadcast_telemetry(self, telemetry_data: Dict[str, Any]):
        with self.ws_lock:
            clients = list(self.active_websockets)
        if not clients:
            return
        for ws in clients:
            try:
                await ws.send_json(telemetry_data)
            except Exception:
                self.unregister_ws(ws)


state = AppState()
