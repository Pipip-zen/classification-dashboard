export type ChannelId = "drone" | "rov";
export type UserRole = "drone" | "rov" | "spectator";

export interface AuthUser {
  username: string;
  role: UserRole;
  display_name: string;
  exp?: number;
}

export interface Detection {
  id?: number;
  track_id?: number;
  class_id: number;
  class_name: string;
  display_name: string;
  confidence: number;
  bbox: [number, number, number, number];
  threat: "HAZARD" | "NEUTRAL";
  threat_label: string;
  color_hex: string;
  estimated_distance_m?: number | null;
}

export interface TelemetryData {
  channel_id?: ChannelId;
  cockpit_mode: ChannelId;
  stream_active?: boolean;
  threat_level: "GREEN SECTOR" | "YELLOW SECTOR" | "RED SECTOR";
  threat_color_hex: string;
  total_objects: number;
  hazard_count: number;
  neutral_count: number;
  fps: number;
  ai_fps?: number;
  latency_ms: number;
  source_type?: string;
  source_param?: string;
  confidence_gate?: number;
  dusk_enhancer?: boolean;
  frame_size?: { width: number; height: number };
  heading_deg?: number;
  cardinal?: string;
  turn_rate_dps?: number;
  compass_calibrated?: boolean;
  tracked_compass_points?: number;
  owner_locked?: boolean;
  owner_label?: string | null;
  detections: Detection[];
}

export interface ChannelStatusSummary {
  channel_id: ChannelId;
  stream_active: boolean;
  source_type: string;
  source_param: string;
  locked: boolean;
  owner_session_id?: string | null;
  owner_label?: string | null;
  fps: number;
  ai_fps: number;
  latency_ms: number;
  confidence_gate: number;
  dusk_enhancer: boolean;
  reticle_visible: boolean;
  labels_visible: boolean;
  telemetry: TelemetryData;
}

export interface SystemHealth {
  status: string;
  ai_model: {
    model_path: string;
    weights_exist: boolean;
    device: string;
    device_name: string;
    cuda_available: boolean;
  };
  environment: {
    python_version: string;
    torch_version: string;
    opencv_version: string;
  };
  streaming: {
    active: boolean;
    source_type: string;
    source_param: string;
    cockpit_mode: ChannelId;
    fps: number;
    latency_ms: number;
  };
  channels?: Record<ChannelId, ChannelStatusSummary>;
}

export interface VideoSourceOption {
  filename: string;
  display_name: string;
  size_mb: number;
}
