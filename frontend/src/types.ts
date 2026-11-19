export interface Detection {
  id?: number;
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
  cockpit_mode: "drone" | "rov";
  threat_level: "GREEN SECTOR" | "YELLOW SECTOR" | "RED SECTOR";
  threat_color_hex: string;
  total_objects: number;
  hazard_count: number;
  neutral_count: number;
  fps: number;
  latency_ms: number;
  source_type?: string;
  source_param?: string;
  confidence_gate?: number;
  dusk_enhancer?: boolean;
  frame_size?: { width: number; height: number };
  detections: Detection[];
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
    cockpit_mode: "drone" | "rov";
    fps: number;
    latency_ms: number;
  };
}

export interface VideoSourceOption {
  filename: string;
  display_name: string;
  size_mb: number;
}
