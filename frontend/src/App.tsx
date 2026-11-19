import React, { useState, useEffect, useRef } from 'react';
import { TopNavbar } from './components/layout/TopNavbar';
import { LiveCockpit } from './pages/LiveCockpit';
import { MediaAnalysis } from './pages/MediaAnalysis';
import { StitchingView } from './pages/StitchingView';
import { InpaintingView } from './pages/InpaintingView';
import { DatasetView } from './pages/DatasetView';
import type { TelemetryData } from './types';

const defaultTelemetry: TelemetryData = {
  cockpit_mode: 'drone',
  threat_level: 'GREEN SECTOR',
  threat_color_hex: '#00FF66',
  total_objects: 0,
  hazard_count: 0,
  neutral_count: 0,
  fps: 0,
  latency_ms: 0,
  detections: []
};

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('live');
  const [cockpitMode, setCockpitMode] = useState<'drone' | 'rov'>('drone');
  const [telemetry, setTelemetry] = useState<TelemetryData>(defaultTelemetry);
  const wsRef = useRef<WebSocket | null>(null);

  // Sinkronisasi mode cockpit ke backend saat diubah di navbar
  const handleCockpitModeChange = async (mode: 'drone' | 'rov') => {
    setCockpitMode(mode);
    try {
      await fetch('/api/stream/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cockpit_mode: mode })
      });
    } catch (e) {
      console.error("Failed to update cockpit mode:", e);
    }
  };

  // WebSocket Connection Lifecycle
  useEffect(() => {
    let reconnectTimer: any;

    const connectWS = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WS] Connected to Tactical Telemetry");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.threat_level) {
            setTelemetry(data);
            if (data.cockpit_mode && data.cockpit_mode !== cockpitMode) {
              setCockpitMode(data.cockpit_mode);
            }
          }
        } catch (e) {
          // ignore heartbeat
        }
      };

      ws.onclose = () => {
        console.log("[WS] Telemetry disconnected. Retrying in 2s...");
        reconnectTimer = setTimeout(connectWS, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWS();

    return () => {
      clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-aerospace-bg text-tactical-text flex flex-col font-sans">
      <TopNavbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        cockpitMode={cockpitMode}
        setCockpitMode={handleCockpitModeChange}
        telemetry={telemetry}
      />

      <main className="flex-1 overflow-auto">
        {activeTab === 'live' && (
          <LiveCockpit cockpitMode={cockpitMode} telemetry={telemetry} />
        )}
        {activeTab === 'analysis' && <MediaAnalysis />}
        {activeTab === 'stitching' && <StitchingView />}
        {activeTab === 'inpainting' && <InpaintingView />}
        {activeTab === 'dataset' && <DatasetView />}
      </main>
    </div>
  );
};

export default App;
