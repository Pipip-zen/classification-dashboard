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
  ChevronLeft, 
  ChevronRight,
  Tv,
  Film,
  Monitor,
  Radio,
  Camera,
  Share2
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

  // Floating Card Minimization
  const [leftCardCollapsed, setLeftCardCollapsed] = useState<boolean>(false);
  const [rightCardCollapsed, setRightCardCollapsed] = useState<boolean>(false);

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

    // Cek status streaming saat ini
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

  // Update Config ke Backend saat slider/toggle berubah
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

  // Start / Stop Stream
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
    { id: 'testbench', label: 'Virtual Testbench', icon: Tv },
    { id: 'youtube', label: 'YouTube Stream', icon: Film },
    { id: 'screen', label: 'Screen Mirroring', icon: Monitor },
    { id: 'network', label: 'Network / RTSP', icon: Radio },
    { id: 'webcam', label: 'USB Webcam', icon: Camera },
    { id: 'tiktok', label: 'TikTok Live', icon: Share2 },
  ];

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] bg-aerospace-stage overflow-hidden flex items-center justify-center">
      {/* 1. FULL-VIEWPORT VIDEO STAGE */}
      <div className="relative w-full h-full flex items-center justify-center">
        <img
          src="/api/stream/feed"
          alt="Tactical Video Stream"
          className="max-w-full max-h-full object-contain pointer-events-none select-none"
        />

        {/* Tactical Corner Brackets */}
        <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-tactical-cyan/40 pointer-events-none" />
        <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-tactical-cyan/40 pointer-events-none" />
        <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-tactical-cyan/40 pointer-events-none" />
        <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-tactical-cyan/40 pointer-events-none" />

        {/* Center Reticle (jika diaktifkan) */}
        {reticleVisible && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="relative w-28 h-28 border border-tactical-cyan/30 rounded-full flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-tactical-cyan/60 animate-ping" />
              <div className="absolute top-0 w-px h-4 bg-tactical-cyan/70" />
              <div className="absolute bottom-0 w-px h-4 bg-tactical-cyan/70" />
              <div className="absolute left-0 w-4 h-px bg-tactical-cyan/70" />
              <div className="absolute right-0 w-4 h-px bg-tactical-cyan/70" />
            </div>
          </div>
        )}
      </div>

      {/* 2. FLOATING CARD LEFT: INPUT STREAM & PARAMETERS */}
      <div 
        className={`absolute top-4 left-4 z-40 transition-all duration-300 ${
          leftCardCollapsed ? 'w-10' : 'w-80'
        }`}
      >
        <div className="tactical-glass rounded-xl shadow-2xl overflow-hidden border border-aerospace-border">
          {/* Card Header */}
          <div className="p-3 bg-aerospace-surface/90 border-b border-aerospace-border flex items-center justify-between">
            {!leftCardCollapsed && (
              <div className="flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-tactical-cyan" />
                <span className="font-mono font-bold text-xs text-white uppercase tracking-wider">
                  KONTROL INPUT STREAM
                </span>
              </div>
            )}
            <button
              onClick={() => setLeftCardCollapsed(!leftCardCollapsed)}
              className="p-1 rounded text-gray-400 hover:text-white hover:bg-aerospace-border/50 transition-all"
            >
              {leftCardCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* Card Body */}
          {!leftCardCollapsed && (
            <div className="p-4 space-y-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
              {/* Sumber Input Selector Grid */}
              <div>
                <label className="text-[11px] font-mono text-gray-400 uppercase tracking-wider block mb-2">
                  Pilih Sumber Input:
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {sourceButtons.map(s => {
                    const Icon = s.icon;
                    const isSelected = sourceType === s.id;
                    return (
                      <button
                        key={s.id}
                        onClick={() => setSourceType(s.id)}
                        className={`flex items-center space-x-2 px-2.5 py-2 rounded text-[11px] font-mono transition-all text-left ${
                          isSelected
                            ? 'bg-aerospace-border text-tactical-cyan border border-tactical-cyan/50 shadow-sm'
                            : 'bg-aerospace-panel/60 text-gray-300 hover:bg-aerospace-border/40'
                        }`}
                      >
                        <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-tactical-cyan' : 'text-gray-400'}`} />
                        <span className="truncate">{s.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Dynamic Input Details */}
              <div className="bg-aerospace-panel/50 p-2.5 rounded-lg border border-aerospace-border">
                {sourceType === 'testbench' && (
                  <div>
                    <label className="text-[10px] font-mono text-gray-400 block mb-1">Pilih Video Testbench:</label>
                    <select
                      value={selectedVideo}
                      onChange={(e) => setSelectedVideo(e.target.value)}
                      className="w-full bg-aerospace-bg border border-aerospace-border rounded px-2 py-1.5 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
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
                    <label className="text-[10px] font-mono text-gray-400 block mb-1">YouTube Video / Live URL:</label>
                    <input
                      type="text"
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      placeholder="https://www.youtube.com/watch?v=..."
                      className="w-full bg-aerospace-bg border border-aerospace-border rounded px-2 py-1.5 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
                    />
                  </div>
                )}

                {sourceType === 'network' && (
                  <div>
                    <label className="text-[10px] font-mono text-gray-400 block mb-1">RTSP / UDP / SDP Path:</label>
                    <input
                      type="text"
                      value={networkUrl}
                      onChange={(e) => setNetworkUrl(e.target.value)}
                      placeholder="udp://192.168.2.1:5602"
                      className="w-full bg-aerospace-bg border border-aerospace-border rounded px-2 py-1.5 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
                    />
                  </div>
                )}

                {sourceType === 'screen' && (
                  <div>
                    <label className="text-[10px] font-mono text-gray-400 block mb-1">Pilih Window Software:</label>
                    <select
                      value={selectedWindow}
                      onChange={(e) => setSelectedWindow(e.target.value)}
                      className="w-full bg-aerospace-bg border border-aerospace-border rounded px-2 py-1.5 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
                    >
                      {activeWindows.map(w => (
                        <option key={w} value={w}>{w}</option>
                      ))}
                    </select>
                  </div>
                )}

                {sourceType === 'webcam' && (
                  <div>
                    <label className="text-[10px] font-mono text-gray-400 block mb-1">Indeks USB Webcam:</label>
                    <input
                      type="number"
                      value={webcamIndex}
                      onChange={(e) => setWebcamIndex(e.target.value)}
                      min="0"
                      max="4"
                      className="w-full bg-aerospace-bg border border-aerospace-border rounded px-2 py-1.5 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
                    />
                  </div>
                )}

                {sourceType === 'tiktok' && (
                  <div>
                    <label className="text-[10px] font-mono text-gray-400 block mb-1">TikTok @Username / URL:</label>
                    <input
                      type="text"
                      value={tiktokUsername}
                      onChange={(e) => setTiktokUsername(e.target.value)}
                      placeholder="@username"
                      className="w-full bg-aerospace-bg border border-aerospace-border rounded px-2 py-1.5 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
                    />
                  </div>
                )}
              </div>

              {/* Start / Stop Button */}
              <div>
                {!isStreaming ? (
                  <button
                    onClick={handleStartStream}
                    disabled={loadingStream}
                    className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-bold text-xs tracking-wider shadow-glow-emerald transition-all"
                  >
                    <Play className="w-4 h-4 fill-white" />
                    <span>{loadingStream ? 'MENGHUBUNGKAN...' : 'MULAI STREAMING PENGAWASAN'}</span>
                  </button>
                ) : (
                  <button
                    onClick={handleStopStream}
                    disabled={loadingStream}
                    className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-mono font-bold text-xs tracking-wider shadow-glow-red transition-all"
                  >
                    <Square className="w-4 h-4 fill-white" />
                    <span>HENTIKAN STREAMING</span>
                  </button>
                )}
              </div>

              {/* Parameter AI Controls */}
              <div className="space-y-3 pt-2 border-t border-aerospace-border">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[11px] font-mono text-gray-300">Confidence Gate:</span>
                    <span className="text-xs font-mono font-bold text-tactical-cyan">
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
                    className="w-full h-1.5 bg-aerospace-panel rounded-lg appearance-none cursor-pointer accent-tactical-cyan"
                  />
                </div>

                {/* Toggles */}
                <div className="space-y-2">
                  <button
                    onClick={handleDuskToggle}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded text-xs font-mono border transition-all ${
                      duskEnhancer
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                        : 'bg-aerospace-panel/60 text-gray-400 border-aerospace-border'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <Moon className="w-3.5 h-3.5" />
                      <span>Dusk / Low-Light Enhancer</span>
                    </div>
                    <span className="font-bold">{duskEnhancer ? 'ON' : 'OFF'}</span>
                  </button>

                  <button
                    onClick={handleReticleToggle}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded text-xs font-mono border transition-all ${
                      reticleVisible
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                        : 'bg-aerospace-panel/60 text-gray-400 border-aerospace-border'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <Crosshair className="w-3.5 h-3.5" />
                      <span>HUD Reticle Crosshair</span>
                    </div>
                    <span className="font-bold">{reticleVisible ? 'ON' : 'OFF'}</span>
                  </button>

                  <button
                    onClick={handleLabelsToggle}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded text-xs font-mono border transition-all ${
                      labelsVisible
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                        : 'bg-aerospace-panel/60 text-gray-400 border-aerospace-border'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      {labelsVisible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                      <span>Label & Bounding Boxes</span>
                    </div>
                    <span className="font-bold">{labelsVisible ? 'ON' : 'OFF'}</span>
                  </button>
                </div>

                {/* Reload Model Button */}
                <button
                  onClick={handleReloadModel}
                  className="w-full flex items-center justify-center space-x-2 py-1.5 rounded bg-aerospace-panel hover:bg-aerospace-border text-gray-300 text-[11px] font-mono border border-aerospace-border transition-all"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Muat Ulang Bobot AI (best.pt)</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. FLOATING CARD RIGHT: TACTICAL THREAT MANIFEST */}
      <div 
        className={`absolute top-4 right-4 z-40 transition-all duration-300 ${
          rightCardCollapsed ? 'w-10' : 'w-80'
        }`}
      >
        <div className="tactical-glass rounded-xl shadow-2xl overflow-hidden border border-aerospace-border">
          {/* Card Header */}
          <div className="p-3 bg-aerospace-surface/90 border-b border-aerospace-border flex items-center justify-between">
            <button
              onClick={() => setRightCardCollapsed(!rightCardCollapsed)}
              className="p-1 rounded text-gray-400 hover:text-white hover:bg-aerospace-border/50 transition-all"
            >
              {rightCardCollapsed ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            {!rightCardCollapsed && (
              <div className="flex items-center space-x-2">
                <span className="font-mono font-bold text-xs text-white uppercase tracking-wider">
                  TELEMETRI TAKTIS & TARGET
                </span>
              </div>
            )}
          </div>

          {/* Card Body */}
          {!rightCardCollapsed && (
            <div className="p-4 space-y-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
              {/* Threat Sector Banner */}
              <div 
                className="p-3 rounded-lg border text-center font-mono"
                style={{
                  backgroundColor: `${telemetry.threat_color_hex}18`,
                  borderColor: `${telemetry.threat_color_hex}70`
                }}
              >
                <div 
                  className="font-bold text-sm tracking-widest uppercase"
                  style={{ color: telemetry.threat_color_hex }}
                >
                  🛡️ {telemetry.threat_level}
                </div>
                <div className="text-[10px] text-gray-300 mt-0.5">
                  {telemetry.hazard_count > 0 
                    ? `Perhatian: ${telemetry.hazard_count} Target Bahaya Terpantau`
                    : 'Sektor Aman: Tidak Ditemukan Kombatan/Ranjau'
                  }
                </div>
              </div>

              {/* Counters */}
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-aerospace-panel/70 p-2.5 rounded-lg border border-aerospace-border text-center">
                  <div className="text-[10px] text-gray-400 font-mono">TOTAL</div>
                  <div className="text-xl font-bold font-mono text-white telemetry-num">
                    {telemetry.total_objects}
                  </div>
                </div>
                <div className="bg-aerospace-panel/70 p-2.5 rounded-lg border border-aerospace-border text-center">
                  <div className="text-[10px] text-tactical-red font-mono">BAHAYA</div>
                  <div className="text-xl font-bold font-mono text-tactical-red telemetry-num">
                    {telemetry.hazard_count}
                  </div>
                </div>
                <div className="bg-aerospace-panel/70 p-2.5 rounded-lg border border-aerospace-border text-center">
                  <div className="text-[10px] text-tactical-emerald font-mono">NETRAL</div>
                  <div className="text-xl font-bold font-mono text-tactical-emerald telemetry-num">
                    {telemetry.neutral_count}
                  </div>
                </div>
              </div>

              {/* Live Target Manifest List */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[11px] font-mono text-gray-400 uppercase tracking-wider">
                    TARGET MANIFEST ({telemetry.detections.length}):
                  </span>
                  <span className="text-[10px] font-mono text-tactical-cyan">LIVE</span>
                </div>

                <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                  {telemetry.detections.length === 0 ? (
                    <div className="text-center py-6 text-xs text-gray-500 font-mono">
                      Tidak ada objek terdeteksi dalam frame
                    </div>
                  ) : (
                    telemetry.detections.map((det, idx) => (
                      <div 
                        key={idx}
                        className="bg-aerospace-panel/80 p-2 rounded border border-aerospace-border flex items-center justify-between text-xs font-mono hover:border-tactical-cyan/40 transition-all"
                      >
                        <div className="flex items-center space-x-2">
                          <span 
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: det.color_hex }}
                          />
                          <div>
                            <div className="font-semibold text-white truncate max-w-[120px]">
                              {det.display_name}
                            </div>
                            <div className="text-[10px] text-gray-400">
                              Conf: {(det.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>

                        <div className="text-right">
                          <span 
                            className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                            style={{
                              backgroundColor: `${det.color_hex}25`,
                              color: det.color_hex
                            }}
                          >
                            {det.threat}
                          </span>
                          {det.estimated_distance_m && (
                            <div className="text-[10px] text-tactical-cyan mt-0.5">
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
        </div>
      </div>
    </div>
  );
};
