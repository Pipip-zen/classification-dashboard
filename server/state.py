"""
Module: server/state.py
Deskripsi:
    Global state container multi-channel (Drone dan ROV) untuk FastAPI backend:
    - Shared AI Model (TacticalDetector) dengan tracker dan kompas terisolasi per channel
    - Channel Lock & Heartbeat untuk mencegah bentrok antar Operator
    - WebSocket Telemetry Broadcaster per channel & backward-compatible legacy feed
"""

import os
import time
import threading
from typing import Dict, Any, Optional, Set, Tuple, List
from fastapi import WebSocket
from pathlib import Path

from core.detector import TacticalDetector
from core.threat_evaluator import ThreatEvaluator
from core.distance_estimator import DistanceEstimator
from core.orientation_estimator import OrientationEstimator
from core.temporal_tracker import TemporalTracker


VALID_CHANNELS = ("drone", "rov")
LOCK_TTL_SECONDS = 15.0


class ChannelState:
    """State operasional, kunci akses operator, dan telemetri untuk satu channel taktis."""

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.cockpit_mode = channel_id
        self.lock = threading.Lock()

        # Isolasi tracker dan kompas per channel agar pelacakan Drone & ROV tidak tercampur
        self.tracker = TemporalTracker(iou_threshold=0.35, max_age=15)
        self.distance_estimator = DistanceEstimator()
        self.orientation_estimator = OrientationEstimator()

        self.confidence_gate: float = 0.25
        self.dusk_enhancer: bool = False
        self.reticle_visible: bool = True
        self.labels_visible: bool = True
        self.compact_hud: bool = False

        self.stream_active: bool = False
        self.source_type: str = "testbench"
        self.source_param: str = (
            "drone_forest_person_patrol.mp4" if channel_id == "drone" else "rov_underwater_patrol.mp4"
        )
        self.current_fps: float = 0.0
        self.ai_fps: float = 0.0
        self.last_latency_ms: float = 0.0

        # Cache deteksi terbaru untuk ditempel pada frame live saat YOLO async masih berjalan
        self.cached_detections: List[Dict[str, Any]] = []
        self.cached_hazard_count: int = 0
        self.cached_neutral_count: int = 0
        self.cached_threat_level: str = "GREEN SECTOR"
        self.cached_threat_color_hex: str = "#00FF66"

        self.owner_session_id: Optional[str] = None
        self.owner_label: Optional[str] = None
        self.locked_at: float = 0.0
        self.last_heartbeat: float = 0.0

        self.latest_telemetry: Dict[str, Any] = self._default_telemetry()

        self.telemetry_websockets: Set[WebSocket] = set()
        self.ws_lock = threading.Lock()

    def _default_telemetry(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "cockpit_mode": self.channel_id,
            "stream_active": False,
            "threat_level": "GREEN SECTOR",
            "threat_color_hex": "#00FF66",
            "total_objects": 0,
            "hazard_count": 0,
            "neutral_count": 0,
            "fps": 0.0,
            "ai_fps": 0.0,
            "latency_ms": 0.0,
            "source_type": self.source_type,
            "source_param": self.source_param,
            "confidence_gate": self.confidence_gate,
            "dusk_enhancer": self.dusk_enhancer,
            "heading_deg": 0.0,
            "cardinal": "N",
            "turn_rate_dps": 0.0,
            "compass_calibrated": False,
            "tracked_compass_points": 0,
            "owner_locked": False,
            "owner_label": None,
            "detections": [],
        }

    def is_lock_expired(self) -> bool:
        if self.owner_session_id is None:
            return True
        return (time.time() - self.last_heartbeat) > LOCK_TTL_SECONDS

    def is_locked_by_other(self, session_id: Optional[str]) -> bool:
        if self.is_lock_expired():
            return False
        if not session_id:
            return True
        return self.owner_session_id != session_id

    def claim(
        self,
        session_id: str,
        owner_label: str = "",
        pin: Optional[str] = None,
        operator_pin: str = "1234",
    ) -> Tuple[bool, str]:
        with self.lock:
            now = time.time()
            if self.is_lock_expired() or self.owner_session_id == session_id:
                self.owner_session_id = session_id
                self.owner_label = owner_label or f"Operator {self.channel_id.upper()}"
                if self.locked_at == 0.0:
                    self.locked_at = now
                self.last_heartbeat = now
                return True, "Channel diklaim"

            if pin is not None and pin == operator_pin:
                self.owner_session_id = session_id
                self.owner_label = owner_label or f"Operator {self.channel_id.upper()}"
                self.locked_at = now
                self.last_heartbeat = now
                return True, "Channel diambil alih dengan PIN"

            return False, f"Channel sedang dipakai oleh {self.owner_label or 'Operator lain'}"

    def release(self, session_id: Optional[str] = None) -> bool:
        with self.lock:
            if self.owner_session_id is None:
                return True
            if session_id not in (None, "*", self.owner_session_id) and not self.is_lock_expired():
                return False
            self.owner_session_id = None
            self.owner_label = None
            self.locked_at = 0.0
            self.last_heartbeat = 0.0
            return True

    def heartbeat(self, session_id: str) -> bool:
        with self.lock:
            if self.owner_session_id == session_id:
                self.last_heartbeat = time.time()
                return True
            return False

    def reset_tracking_state(self) -> None:
        self.tracker = TemporalTracker(iou_threshold=0.35, max_age=15)
        self.orientation_estimator.reset()
        self.cached_detections = []
        self.cached_hazard_count = 0
        self.cached_neutral_count = 0
        self.cached_threat_level = "GREEN SECTOR"
        self.cached_threat_color_hex = "#00FF66"

    def update_config(self, **kwargs):
        with self.lock:
            for k, v in kwargs.items():
                if k == "cockpit_mode":
                    continue
                if hasattr(self, k) and v is not None:
                    setattr(self, k, v)
            self.latest_telemetry["confidence_gate"] = self.confidence_gate
            self.latest_telemetry["dusk_enhancer"] = self.dusk_enhancer

    def status_summary(self) -> Dict[str, Any]:
        expired = self.is_lock_expired()
        return {
            "channel_id": self.channel_id,
            "stream_active": self.stream_active,
            "source_type": self.source_type,
            "source_param": self.source_param,
            "locked": not expired and self.owner_session_id is not None,
            "owner_session_id": None if expired else self.owner_session_id,
            "owner_label": None if expired else self.owner_label,
            "fps": self.current_fps,
            "ai_fps": self.ai_fps,
            "latency_ms": self.last_latency_ms,
            "confidence_gate": self.confidence_gate,
            "dusk_enhancer": self.dusk_enhancer,
            "reticle_visible": self.reticle_visible,
            "labels_visible": self.labels_visible,
            "telemetry": self.latest_telemetry,
        }

    async def register_ws(self, ws: WebSocket):
        with self.ws_lock:
            self.telemetry_websockets.add(ws)

    def unregister_ws(self, ws: WebSocket):
        with self.ws_lock:
            self.telemetry_websockets.discard(ws)

    async def broadcast(self, telemetry_data: Dict[str, Any]):
        with self.ws_lock:
            clients = list(self.telemetry_websockets)
        if not clients:
            return
        for ws in clients:
            try:
                await ws.send_json(telemetry_data)
            except Exception:
                self.unregister_ws(ws)


class AppState:
    def __init__(self):
        self.lock = threading.Lock()

        base_dir = Path(__file__).resolve().parent.parent
        model_path = base_dir / "models" / "best.pt"
        if not model_path.exists():
            model_path = base_dir / "models" / "yolov8n.pt"

        self.model_path = str(model_path)
        self.detector = TacticalDetector(self.model_path)
        self.threat_evaluator = ThreatEvaluator()
        self.operator_pin = os.getenv("OPERATOR_PIN", "1234")

        self.channels: Dict[str, ChannelState] = {
            cid: ChannelState(cid) for cid in VALID_CHANNELS
        }
        self.active_channel_id: str = "drone"

        self.active_websockets: Set[WebSocket] = set()
        self.ws_lock = threading.Lock()

    def get_channel(self, channel_id: Optional[str] = None) -> ChannelState:
        cid = (channel_id or self.active_channel_id).lower()
        if cid not in self.channels:
            cid = self.active_channel_id
        return self.channels[cid]

    @property
    def active_channel(self) -> ChannelState:
        return self.channels[self.active_channel_id]

    @property
    def cockpit_mode(self) -> str:
        return self.active_channel_id

    @cockpit_mode.setter
    def cockpit_mode(self, value: str):
        if value in self.channels:
            self.active_channel_id = value

    @property
    def orientation_estimator(self) -> OrientationEstimator:
        return self.active_channel.orientation_estimator

    @property
    def distance_estimator(self) -> DistanceEstimator:
        return self.active_channel.distance_estimator

    @property
    def confidence_gate(self) -> float:
        return self.active_channel.confidence_gate

    @property
    def dusk_enhancer(self) -> bool:
        return self.active_channel.dusk_enhancer

    @property
    def reticle_visible(self) -> bool:
        return self.active_channel.reticle_visible

    @property
    def labels_visible(self) -> bool:
        return self.active_channel.labels_visible

    @property
    def compact_hud(self) -> bool:
        return self.active_channel.compact_hud

    @property
    def stream_active(self) -> bool:
        return self.active_channel.stream_active

    @stream_active.setter
    def stream_active(self, val: bool):
        self.active_channel.stream_active = val

    @property
    def source_type(self) -> str:
        return self.active_channel.source_type

    @source_type.setter
    def source_type(self, val: str):
        self.active_channel.source_type = val

    @property
    def source_param(self) -> str:
        return self.active_channel.source_param

    @source_param.setter
    def source_param(self, val: str):
        self.active_channel.source_param = val

    @property
    def current_fps(self) -> float:
        return self.active_channel.current_fps

    @current_fps.setter
    def current_fps(self, val: float):
        self.active_channel.current_fps = val

    @property
    def last_latency_ms(self) -> float:
        return self.active_channel.last_latency_ms

    @last_latency_ms.setter
    def last_latency_ms(self, val: float):
        self.active_channel.last_latency_ms = val

    @property
    def latest_telemetry(self) -> Dict[str, Any]:
        return self.active_channel.latest_telemetry

    def update_config(self, channel_id: Optional[str] = None, **kwargs):
        if channel_id is None and "cockpit_mode" in kwargs and kwargs["cockpit_mode"] in self.channels:
            self.active_channel_id = kwargs["cockpit_mode"]
        ch = self.get_channel(channel_id)
        ch.update_config(**kwargs)

    def reload_detector(self) -> bool:
        with self.lock:
            try:
                self.detector = TacticalDetector(self.model_path)
                return True
            except Exception as e:
                print(f"[ERROR] Gagal memuat ulang detector: {e}")
                return False

    async def register_ws(self, ws: WebSocket, channel_id: Optional[str] = None):
        if channel_id and channel_id in self.channels:
            await self.channels[channel_id].register_ws(ws)
            return
        with self.ws_lock:
            self.active_websockets.add(ws)

    def unregister_ws(self, ws: WebSocket, channel_id: Optional[str] = None):
        if channel_id and channel_id in self.channels:
            self.channels[channel_id].unregister_ws(ws)
            return
        with self.ws_lock:
            self.active_websockets.discard(ws)

    async def broadcast_telemetry(self, telemetry_data: Dict[str, Any], channel_id: Optional[str] = None):
        cid = channel_id or telemetry_data.get("channel_id") or self.active_channel_id
        ch = self.get_channel(cid)
        await ch.broadcast(telemetry_data)

        if cid == self.active_channel_id:
            with self.ws_lock:
                clients = list(self.active_websockets)
            for ws in clients:
                try:
                    await ws.send_json(telemetry_data)
                except Exception:
                    self.unregister_ws(ws)


state = AppState()
