import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Square, 
  Sliders, 
  Eye, 
  EyeOff, 
  Crosshair, 
  Moon, 
  RefreshCw, 
  Tv,
  Film,
  Monitor,
  Radio,
  Camera,
  Share2,
  ListFilter
} from 'lucide-react';
import type { TelemetryData, VideoSourceOption } from '../types';

interface LiveCockpitProps {
  cockpitMode: 'drone' | 'rov';
  telemetry: TelemetryData;
}

export const LiveCockpit: React.FC<LiveCockpitProps> = ({
  cockpitMode,
  telemetry,
}) => {
  // Active Sidebar Tab
  const [sidebarTab, setSidebarTab] = useState<'input' | 'telemetry' | 'params'>('input');

  // Source State
  const [sourceType, setSourceType] = useState<string>('testbench');
  const [testbenchVideos, setTestbenchVideos] = useState<VideoSourceOption[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<string>('drone_forest_person_patrol.mp4');
  const [youtubeUrl, setYoutubeUrl] = useState<string>('https://www.youtube.com/watch?v=5GBrU0s-2UU');
  const [networkUrl, setNetworkUrl] = useState<string>('udp://192.168.2.1:5602');
  const [activeWindows, setActiveWindows] = useState<string[]>([]);
  const [selectedWindow, setSelectedWindow] = useState<string>('');
  const [webcamIndex, setWebcamIndex] = useState<string>('0');
  const [tiktokUsername, setTiktokUsername] = useState<string>('@blueocean_explorer');

  // Streaming State
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [loadingStream, setLoadingStream] = useState<boolean>(false);

  // HUD & AI Parameters
  const [confidenceGate, setConfidenceGate] = useState<number>(0.25);
  const [duskEnhancer, setDuskEnhancer] = useState<boolean>(false);
  const [reticleVisible, setReticleVisible] = useState<boolean>(true);
  const [labelsVisible, setLabelsVisible] = useState<boolean>(true);

  // Fetch available sources on mount
  useEffect(() => {
    fetch('/api/stream/sources')
      .then(res => res.json())
      .then(data => {
        if (data.testbench_videos) {
          setTestbenchVideos(data.testbench_videos);
          if (cockpitMode === 'rov' && data.default_rov_video) {
            setSelectedVideo(data.default_rov_video);
          } else if (data.default_drone_video) {
            setSelectedVideo(data.default_drone_video);
          }
        }
        if (data.active_windows && data.active_windows.length > 0) {
          setActiveWindows(data.active_windows);
          setSelectedWindow(data.active_windows[0]);
        }
      })
      .catch(err => console.error("Error fetching sources:", err));

    fetch('/api/stream/status')
      .then(res => res.json())
      .then(data => {
        if (data.stream_active) {
          setIsStreaming(true);
          setSourceType(data.source_type);
        }
        if (data.confidence_gate !== undefined) setConfidenceGate(data.confidence_gate);
        if (data.dusk_enhancer !== undefined) setDuskEnhancer(data.dusk_enhancer);
      })
      .catch(err => console.error("Error fetching stream status:", err));
  }, [cockpitMode]);

  const updateBackendConfig = async (patch: Record<string, any>) => {
    try {
      await fetch('/api/stream/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch)
      });
    } catch (e) {
      console.error("Failed to update config:", e);
    }
  };

  const handleConfidenceChange = (val: number) => {
    setConfidenceGate(val);
    updateBackendConfig({ confidence_gate: val });
  };

  const handleDuskToggle = () => {
    const nextVal = !duskEnhancer;
    setDuskEnhancer(nextVal);
    updateBackendConfig({ dusk_enhancer: nextVal });
  };

  const handleReticleToggle = () => {
    const nextVal = !reticleVisible;
    setReticleVisible(nextVal);
    updateBackendConfig({ reticle_visible: nextVal });
  };

  const handleLabelsToggle = () => {
    const nextVal = !labelsVisible;
    setLabelsVisible(nextVal);
    updateBackendConfig({ labels_visible: nextVal });
  };

  const handleStartStream = async () => {
    setLoadingStream(true);
    let param = '';
    if (sourceType === 'testbench') param = selectedVideo;
    else if (sourceType === 'youtube') param = youtubeUrl;
    else if (sourceType === 'network') param = networkUrl;
    else if (sourceType === 'screen') param = selectedWindow;
    else if (sourceType === 'webcam') param = webcamIndex;
    else if (sourceType === 'tiktok') param = tiktokUsername;

    try {
      const res = await fetch('/api/stream/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_type: sourceType, source_param: param })
      });
      const data = await res.json();
      if (data.success) {
        setIsStreaming(true);
      } else {
        alert(data.error || "Gagal memulai streaming");
      }
    } catch (e) {
      alert("Error menghubungi server backend");
    } finally {
      setLoadingStream(false);
    }
  };

  const handleStopStream = async () => {
    setLoadingStream(true);
    try {
      await fetch('/api/stream/stop', { method: 'POST' });
      setIsStreaming(false);
    } catch (e) {
      console.error("Error stopping stream:", e);
    } finally {
      setLoadingStream(false);
    }
  };

  const handleReloadModel = async () => {
    try {
      const res = await fetch('/api/system/reload-model', { method: 'POST' });
      const data = await res.json();
      alert(data.message);
    } catch (e) {
      alert("Gagal memuat ulang model");
    }
  };

  const sourceButtons = [
    { id: 'testbench', label: 'Testbench MP4', icon: Tv },
    { id: 'youtube', label: 'YouTube URL', icon: Film },
    { id: 'screen', label: 'Screen Mirror', icon: Monitor },
    { id: 'network', label: 'RTSP / UDP', icon: Radio },
    { id: 'webcam', label: 'USB Webcam', icon: Camera },
    { id: 'tiktok', label: 'TikTok Live', icon: Share2 },
  ];

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-3.5rem)] w-full overflow-hidden bg-slate-950">
      {/* 1. MAIN STAGE: VIDEO CANVAS BERSIH (70% - 100% Tanpa Halangan) */}
      <div className="flex-1 h-full flex flex-col relative overflow-hidden bg-black">
        {/* Video Stage Frame */}
        <div className="flex-1 relative flex items-center justify-center overflow-hidden">
          <img
            src="/api/stream/feed"
            alt="VANGUARD Video Stream"
            className="w-full h-full object-contain pointer-events-none select-none"
          />

          {/* Subdued Reticle Crosshair */}
          {reticleVisible && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="relative w-24 h-24 border border-slate-400/40 rounded-full flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-signal-cyan/80" />
                <div className="absolute top-0 w-px h-3 bg-slate-300/60" />
                <div className="absolute bottom-0 w-px h-3 bg-slate-300/60" />
                <div className="absolute left-0 w-3 h-px bg-slate-300/60" />
                <div className="absolute right-0 w-3 h-px bg-slate-300/60" />
              </div>
            </div>
          )}

          {/* Minimalist Top OSD Badge */}
          <div className="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-sm border border-slate-700/60 px-2.5 py-1 rounded text-[11px] font-mono text-slate-300 flex items-center space-x-2">
            <span className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-signal-green' : 'bg-slate-500'}`} />
            <span className="font-semibold uppercase tracking-wider">
              {cockpitMode === 'drone' ? 'DRONE SPECTATOR' : 'ROV DANAU'}
            </span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400">{sourceType.toUpperCase()}</span>
          </div>

          {/* Minimalist Threat Sector Badge */}
          <div 
            className="absolute top-3 right-3 px-2.5 py-1 rounded text-[11px] font-mono font-bold uppercase tracking-wider border backdrop-blur-sm"
            style={{
              backgroundColor: `${telemetry.threat_color_hex}20`,
              borderColor: `${telemetry.threat_color_hex}70`,
              color: telemetry.threat_color_hex
            }}
          >
            {telemetry.threat_level}
          </div>
        </div>
      </div>

      {/* 2. DEDICATED RIGHT SIDEBAR WORKSTATION (30% / 360px - Anti Nabrak) */}
      <div className="w-full lg:w-96 shrink-0 h-auto lg:h-full bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 flex flex-col z-20">
        {/* Sidebar Nav Tabs */}
        <div className="grid grid-cols-3 border-b border-slate-800 bg-slate-950/70 p-1 gap-1">
          <button
            type="button"
            onClick={() => setSidebarTab('input')}
            className={`flex items-center justify-center space-x-1.5 py-2 rounded text-xs font-mono font-medium transition-colors ${
              sidebarTab === 'input'
                ? 'bg-slate-800 text-white border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Tv className="w-3.5 h-3.5" />
            <span>Sinyal</span>
          </button>
          <button
            type="button"
            onClick={() => setSidebarTab('telemetry')}
            className={`flex items-center justify-center space-x-1.5 py-2 rounded text-xs font-mono font-medium transition-colors ${
              sidebarTab === 'telemetry'
                ? 'bg-slate-800 text-white border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ListFilter className="w-3.5 h-3.5" />
            <span>Target ({telemetry.total_objects})</span>
          </button>
          <button
            type="button"
            onClick={() => setSidebarTab('params')}
            className={`flex items-center justify-center space-x-1.5 py-2 rounded text-xs font-mono font-medium transition-colors ${
              sidebarTab === 'params'
                ? 'bg-slate-800 text-white border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>AI OSD</span>
          </button>
        </div>

        {/* Tab 1: Sinyal Input */}
        {sidebarTab === 'input' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div>
              <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-2">
                Pilih Sumber Input:
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {sourceButtons.map(s => {
                  const Icon = s.icon;
                  const isSelected = sourceType === s.id;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setSourceType(s.id)}
                      className={`flex items-center space-x-2 px-2.5 py-2 rounded text-xs font-mono transition-colors text-left ${
                        isSelected
                          ? 'bg-slate-800 text-signal-cyan border border-slate-700'
                          : 'bg-slate-850 text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-signal-cyan' : 'text-slate-500'}`} />
                      <span className="truncate">{s.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Input Options Body */}
            <div className="bg-slate-950 p-3 rounded border border-slate-800 space-y-2">
              {sourceType === 'testbench' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">Pilih Video Testbench:</label>
                  <select
                    value={selectedVideo}
                    onChange={(e) => setSelectedVideo(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  >
                    {testbenchVideos.map(v => (
                      <option key={v.filename} value={v.filename}>
                        {v.display_name} ({v.size_mb} MB)
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {sourceType === 'youtube' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">YouTube URL:</label>
                  <input
                    type="text"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  />
                </div>
              )}

              {sourceType === 'network' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">RTSP / UDP / SDP Path:</label>
                  <input
                    type="text"
                    value={networkUrl}
                    onChange={(e) => setNetworkUrl(e.target.value)}
                    placeholder="udp://192.168.2.1:5602"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  />
                </div>
              )}

              {sourceType === 'screen' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">Pilih Window Software:</label>
                  <select
                    value={selectedWindow}
                    onChange={(e) => setSelectedWindow(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  >
                    {activeWindows.map(w => (
                      <option key={w} value={w}>{w}</option>
                    ))}
                  </select>
                </div>
              )}

              {sourceType === 'webcam' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">Indeks USB Webcam:</label>
                  <input
                    type="number"
                    value={webcamIndex}
                    onChange={(e) => setWebcamIndex(e.target.value)}
                    min="0"
                    max="4"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  />
                </div>
              )}

              {sourceType === 'tiktok' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">TikTok @Username:</label>
                  <input
                    type="text"
                    value={tiktokUsername}
                    onChange={(e) => setTiktokUsername(e.target.value)}
                    placeholder="@username"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  />
                </div>
              )}
            </div>

            {/* Start / Stop Button */}
            <div>
              {!isStreaming ? (
                <button
                  type="button"
                  onClick={handleStartStream}
                  disabled={loadingStream}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-semibold text-xs tracking-wider transition-colors disabled:opacity-50"
                >
                  <Play className="w-4 h-4 fill-white" />
                  <span>{loadingStream ? 'MENGHUBUNGKAN...' : 'MULAI STREAMING'}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStopStream}
                  disabled={loadingStream}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 rounded bg-red-600 hover:bg-red-500 text-white font-mono font-semibold text-xs tracking-wider transition-colors"
                >
                  <Square className="w-4 h-4 fill-white" />
                  <span>HENTIKAN STREAMING</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Target & Telemetri */}
        {sidebarTab === 'telemetry' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Status Sektor Card */}
            <div 
              className="p-3 rounded border text-center font-mono"
              style={{
                backgroundColor: `${telemetry.threat_color_hex}15`,
                borderColor: `${telemetry.threat_color_hex}50`,
                color: telemetry.threat_color_hex
              }}
            >
              <div className="font-bold text-xs uppercase tracking-wider">
                {telemetry.threat_level}
              </div>
              <div className="text-[11px] text-slate-300 mt-0.5">
                {telemetry.hazard_count > 0 
                  ? `${telemetry.hazard_count} Target Bahaya Terpantau`
                  : 'Sektor Aman: Tidak Ditemukan Ancaman'
                }
              </div>
            </div>

            {/* Ringkasan Angka */}
            <div className="grid grid-cols-3 gap-2 text-center font-mono">
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-400">TOTAL</div>
                <div className="text-lg font-bold text-white font-telemetry">{telemetry.total_objects}</div>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-signal-red">BAHAYA</div>
                <div className="text-lg font-bold text-signal-red font-telemetry">{telemetry.hazard_count}</div>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-signal-green">NETRAL</div>
                <div className="text-lg font-bold text-signal-green font-telemetry">{telemetry.neutral_count}</div>
              </div>
            </div>

            {/* Target Manifest List */}
            <div>
              <div className="flex justify-between items-center mb-2 text-[11px] font-mono text-slate-400 uppercase">
                <span>Daftar Target Terdeteksi:</span>
                <span>{telemetry.detections.length} Objek</span>
              </div>

              <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
                {telemetry.detections.length === 0 ? (
                  <div className="text-center py-8 text-xs text-slate-500 font-mono">
                    Tidak ada objek terdeteksi dalam frame
                  </div>
                ) : (
                  telemetry.detections.map((det, idx) => (
                    <div 
                      key={idx}
                      className="bg-slate-950 p-2 rounded border border-slate-800 flex items-center justify-between text-xs font-mono"
                    >
                      <div className="flex items-center space-x-2">
                        <span 
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: det.color_hex }}
                        />
                        <div className="truncate max-w-[130px]">
                          <div className="font-semibold text-white truncate">{det.display_name}</div>
                          <div className="text-[10px] text-slate-400">
                            Conf: {(det.confidence * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <span 
                          className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                          style={{
                            backgroundColor: `${det.color_hex}20`,
                            color: det.color_hex
                          }}
                        >
                          {det.threat}
                        </span>
                        {det.estimated_distance_m && (
                          <div className="text-[10px] text-signal-cyan mt-0.5 font-telemetry">
                            ~{det.estimated_distance_m}m
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Parameter AI & OSD */}
        {sidebarTab === 'params' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div>
              <div className="flex justify-between items-center mb-1 text-xs font-mono">
                <span className="text-slate-300">Ambang Batas (Confidence):</span>
                <span className="font-bold text-signal-cyan font-telemetry">
                  {(confidenceGate * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.95"
                step="0.05"
                value={confidenceGate}
                onChange={(e) => handleConfidenceChange(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-950 rounded appearance-none cursor-pointer accent-signal-cyan"
              />
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={handleDuskToggle}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-mono border transition-colors ${
                  duskEnhancer
                    ? 'bg-amber-900/30 text-amber-200 border-amber-600/50'
                    : 'bg-slate-950 text-slate-400 border-slate-800'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Moon className="w-3.5 h-3.5" />
                  <span>Dusk / Low-Light Enhancer</span>
                </div>
                <span className="font-bold">{duskEnhancer ? 'ON' : 'OFF'}</span>
              </button>

              <button
                type="button"
                onClick={handleReticleToggle}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-mono border transition-colors ${
                  reticleVisible
                    ? 'bg-cyan-900/30 text-cyan-200 border-cyan-600/50'
                    : 'bg-slate-950 text-slate-400 border-slate-800'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Crosshair className="w-3.5 h-3.5" />
                  <span>HUD Reticle Crosshair</span>
                </div>
                <span className="font-bold">{reticleVisible ? 'ON' : 'OFF'}</span>
              </button>

              <button
                type="button"
                onClick={handleLabelsToggle}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-mono border transition-colors ${
                  labelsVisible
                    ? 'bg-emerald-900/30 text-emerald-200 border-emerald-600/50'
                    : 'bg-slate-950 text-slate-400 border-slate-800'
                }`}
              >
                <div className="flex items-center space-x-2">
                  {labelsVisible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                  <span>Label & Bounding Boxes</span>
                </div>
                <span className="font-bold">{labelsVisible ? 'ON' : 'OFF'}</span>
              </button>
            </div>

            <div className="pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={handleReloadModel}
                className="w-full flex items-center justify-center space-x-2 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Muat Ulang Bobot AI (best.pt)</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
