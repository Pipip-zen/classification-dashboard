import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  ListFilter,
  Compass,
  RotateCcw,
  Lock,
  Upload,
} from 'lucide-react';
import type { ChannelId, TelemetryData, VideoSourceOption } from '../../types';
import { getOperatorSessionId, buildWsUrl } from '../../utils/session';
import { authFetch, getAuthToken } from '../../utils/auth';
import { CompassRibbon, CircularCompassDial } from './CompassHUD';
import { RemoteStreamCanvas } from './RemoteStreamCanvas';
import { LocalOverlayCanvas } from './LocalOverlayCanvas';
import { TargetManifestPanel } from './TargetManifestPanel';

interface OperatorViewProps {
  channelId: ChannelId;
  telemetry: TelemetryData;
  onLocalTelemetry: (channelId: ChannelId, telemetry: TelemetryData) => void;
}

type OperatorSourceType =
  | 'window'
  | 'webcam'
  | 'local_file'
  | 'testbench'
  | 'network'
  | 'youtube'
  | 'tiktok';

export const OperatorView: React.FC<OperatorViewProps> = ({
  channelId,
  telemetry,
  onLocalTelemetry,
}) => {
  const sessionIdRef = useRef<string>(getOperatorSessionId());

  const [sidebarTab, setSidebarTab] = useState<'input' | 'telemetry' | 'params'>('input');
  const [sourceType, setSourceType] = useState<OperatorSourceType>('window');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isBrowserPush, setIsBrowserPush] = useState<boolean>(false);
  const [loadingStream, setLoadingStream] = useState<boolean>(false);
  const [streamError, setStreamError] = useState<string>('');

  // Lock state
  const [hasLock, setHasLock] = useState<boolean>(false);
  const [lockedByOther, setLockedByOther] = useState<boolean>(false);
  const [lockOwnerLabel, setLockOwnerLabel] = useState<string>('Operator lain');
  const [takeoverPin, setTakeoverPin] = useState<string>('');
  const [lockError, setLockError] = useState<string>('');

  // Source params
  const [testbenchVideos, setTestbenchVideos] = useState<VideoSourceOption[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<string>(
    channelId === 'rov' ? 'rov_underwater_patrol.mp4' : 'drone_forest_person_patrol.mp4'
  );
  const [youtubeUrl, setYoutubeUrl] = useState<string>('');
  const [networkUrl, setNetworkUrl] = useState<string>('udp://192.168.2.1:5602');
  const [tiktokUsername, setTiktokUsername] = useState<string>('');
  const [localFile, setLocalFile] = useState<File | null>(null);

  // Per-channel AI & OSD configs
  const [confidenceGate, setConfidenceGate] = useState<number>(0.25);
  const [duskEnhancer, setDuskEnhancer] = useState<boolean>(false);
  const [reticleVisible, setReticleVisible] = useState<boolean>(true);
  const [labelsVisible, setLabelsVisible] = useState<boolean>(true);
  const [compassVisible, setCompassVisible] = useState<boolean>(true);
  const [calibratingCompass, setCalibratingCompass] = useState<boolean>(false);
  const [manualOffset, setManualOffset] = useState<number>(0);

  // Browser capture & WebSocket ingest refs
  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const localFileUrlRef = useRef<string | null>(null);
  const ingestWsRef = useRef<WebSocket | null>(null);
  const pumpTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [localVideoDims, setLocalVideoDims] = useState<{ w: number; h: number }>({ w: 960, h: 540 });

  const cleanupBrowserIngest = useCallback(() => {
    if (pumpTimerRef.current) {
      clearInterval(pumpTimerRef.current);
      pumpTimerRef.current = null;
    }
    if (ingestWsRef.current) {
      if (ingestWsRef.current.readyState < WebSocket.CLOSING) {
        ingestWsRef.current.close();
      }
      ingestWsRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (localFileUrlRef.current) {
      URL.revokeObjectURL(localFileUrlRef.current);
      localFileUrlRef.current = null;
    }
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
      localVideoRef.current.removeAttribute('src');
    }
    setIsBrowserPush(false);
    setIsStreaming(false);
  }, []);

  const applyClaimResponse = useCallback(
    (data: {
      success?: boolean;
      channel?: {
        owner_label?: string;
        confidence_gate?: number;
        dusk_enhancer?: boolean;
        reticle_visible?: boolean;
        labels_visible?: boolean;
      };
    }, usedPin?: string) => {
      if (data.success) {
        setHasLock(true);
        setLockedByOther(false);
        setTakeoverPin('');
        setLockError('');
        if (data.channel) {
          setConfidenceGate(data.channel.confidence_gate ?? 0.25);
          setDuskEnhancer(data.channel.dusk_enhancer ?? false);
          setReticleVisible(data.channel.reticle_visible ?? true);
          setLabelsVisible(data.channel.labels_visible ?? true);
        }
      } else {
        setHasLock(false);
        setLockedByOther(true);
        setLockOwnerLabel(data.channel?.owner_label || 'Operator lain');
        if (usedPin) {
          setLockError('PIN tidak valid atau ditolak server.');
        }
      }
    },
    []
  );

  const claimChannel = useCallback(
    async (pin?: string) => {
      setLockError('');
      try {
        const res = await authFetch(`/api/channels/${channelId}/claim`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionIdRef.current,
            owner_label: `Admin ${channelId.toUpperCase()}`,
            pin: pin || undefined,
          }),
        });
        const data = await res.json();
        applyClaimResponse(data, pin);
      } catch {
        setLockError('Gagal menghubungi server untuk klaim channel.');
      }
    },
    [channelId, applyClaimResponse]
  );

  useEffect(() => {
    const sid = sessionIdRef.current;
    const tokenSnapshot = getAuthToken();
    let active = true;

    authFetch(`/api/channels/${channelId}/claim`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sid,
        owner_label: `Admin ${channelId.toUpperCase()}`,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (active) applyClaimResponse(data);
      })
      .catch(() => {
        if (active) setLockError('Gagal menghubungi server untuk klaim channel.');
      });

    authFetch('/api/stream/sources')
      .then((res) => res.json())
      .then((data) => {
        if (!active || !data.testbench_videos) return;
        setTestbenchVideos(data.testbench_videos);
        if (channelId === 'rov' && data.default_rov_video) {
          setSelectedVideo(data.default_rov_video);
        } else if (data.default_drone_video) {
          setSelectedVideo(data.default_drone_video);
        }
      })
      .catch(() => {});

    const releaseViaBeacon = () => {
      const tok = getAuthToken() || tokenSnapshot || '';
      const payload = new Blob([JSON.stringify({ session_id: sid })], { type: 'application/json' });
      navigator.sendBeacon(
        `/api/channels/${channelId}/release?token=${encodeURIComponent(tok)}`,
        payload
      );
    };

    window.addEventListener('beforeunload', releaseViaBeacon);

    return () => {
      active = false;
      window.removeEventListener('beforeunload', releaseViaBeacon);
      cleanupBrowserIngest();
      const tok = getAuthToken() || tokenSnapshot;
      if (tok) {
        fetch(`/api/channels/${channelId}/release`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${tok}`,
          },
          body: JSON.stringify({ session_id: sid }),
        }).catch(() => {});
      }
    };
  }, [channelId, applyClaimResponse, cleanupBrowserIngest]);

  useEffect(() => {
    if (!hasLock) return;
    const timer = setInterval(() => {
      authFetch(`/api/channels/${channelId}/heartbeat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionIdRef.current }),
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(timer);
  }, [channelId, hasLock]);

  const updateChannelConfig = async (patch: Record<string, unknown>) => {
    try {
      await authFetch(`/api/channels/${channelId}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
    } catch {
      // Abaikan gangguan sementara saat update slider
    }
  };

  const handleSetNorth = async () => {
    setCalibratingCompass(true);
    try {
      await authFetch(`/api/channels/${channelId}/compass/calibrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'set_north' }),
      });
      setManualOffset(0);
    } finally {
      setCalibratingCompass(false);
    }
  };

  const handleApplyOffset = async (offsetVal: number) => {
    setManualOffset(offsetVal);
    await authFetch(`/api/channels/${channelId}/compass/calibrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'set_offset', offset_deg: offsetVal }),
    }).catch(() => {});
  };

  const startBrowserPushPipeline = async (
    label: string,
    opts: { stream?: MediaStream; file?: File }
  ) => {
    // Bersihkan sesi lama dulu sebelum menyimpan stream baru ke ref agar track baru tidak ikut di-stop
    cleanupBrowserIngest();

    const videoEl = localVideoRef.current;
    if (!videoEl) {
      opts.stream?.getTracks().forEach((t) => t.stop());
      setStreamError('Elemen video lokal belum siap.');
      return;
    }

    if (opts.stream) {
      mediaStreamRef.current = opts.stream;
      const track = opts.stream.getVideoTracks()[0];
      if (track) {
        track.onended = () => cleanupBrowserIngest();
      }
      videoEl.loop = false;
      videoEl.srcObject = opts.stream;
    } else if (opts.file) {
      const objUrl = URL.createObjectURL(opts.file);
      localFileUrlRef.current = objUrl;
      videoEl.srcObject = null;
      videoEl.src = objUrl;
      videoEl.loop = true;
    }

    setIsBrowserPush(true);

    // Tunggu metadata dimensi video siap sebelum memutar dan memompa frame ke canvas
    if (videoEl.readyState < 1) {
      await new Promise<void>((resolve) => {
        const onReady = () => {
          videoEl.removeEventListener('loadedmetadata', onReady);
          resolve();
        };
        videoEl.addEventListener('loadedmetadata', onReady);
      });
    }
    await videoEl.play();

    const wsUrl = buildWsUrl(
      `/ws/ingest/${channelId}?session_id=${encodeURIComponent(sessionIdRef.current)}&source_label=${encodeURIComponent(label)}`
    );
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    ingestWsRef.current = ws;

    if (!captureCanvasRef.current) {
      captureCanvasRef.current = document.createElement('canvas');
    }

    ws.onopen = () => {
      setIsStreaming(true);
      pumpTimerRef.current = setInterval(() => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        // Lewati frame jika buffer WebSocket masih padat agar latensi tidak menumpuk
        if (ws.bufferedAmount > 256 * 1024) return;

        const vid = localVideoRef.current;
        const canvas = captureCanvasRef.current;
        if (!vid || !canvas || vid.videoWidth <= 0 || vid.videoHeight <= 0 || vid.paused || vid.ended) {
          return;
        }

        const maxW = 960;
        const maxH = 540;
        const scale = Math.min(1, maxW / vid.videoWidth, maxH / vid.videoHeight);
        const tw = Math.max(2, Math.round(vid.videoWidth * scale));
        const th = Math.max(2, Math.round(vid.videoHeight * scale));

        if (canvas.width !== tw || canvas.height !== th) {
          canvas.width = tw;
          canvas.height = th;
          setLocalVideoDims({ w: tw, h: th });
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.drawImage(vid, 0, 0, tw, th);
        canvas.toBlob(
          (blob) => {
            if (blob && ws.readyState === WebSocket.OPEN) {
              ws.send(blob);
            }
          },
          'image/jpeg',
          0.72
        );
      }, 66);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'lock_rejected') {
          setStreamError(msg.error || 'Channel terkunci Operator lain');
          setLockedByOther(true);
          setHasLock(false);
          cleanupBrowserIngest();
        } else if (msg.telemetry) {
          onLocalTelemetry(channelId, msg.telemetry);
        }
      } catch {
        // Abaikan pesan non-JSON
      }
    };

    ws.onclose = (event) => {
      if (pumpTimerRef.current) {
        clearInterval(pumpTimerRef.current);
        pumpTimerRef.current = null;
      }
      if (event.code === 4001) {
        setStreamError('Sesi otentikasi WebSocket kedaluwarsa. Silakan login ulang.');
        cleanupBrowserIngest();
      } else if (event.code === 4003) {
        setStreamError('Koneksi ingest ditolak (peran tidak sesuai atau channel sedang terkunci).');
        cleanupBrowserIngest();
      } else {
        setIsStreaming(false);
      }
    };

    ws.onerror = () => {
      setStreamError('Koneksi ingest WebSocket ke server gagal atau terputus.');
      cleanupBrowserIngest();
    };
  };

  const handleStartStream = async () => {
    setStreamError('');
    setLoadingStream(true);

    try {
      if (sourceType === 'window') {
        if (!navigator.mediaDevices?.getDisplayMedia) {
          throw new Error(
            'Browser tidak mendukung Screen/Window Capture di alamat ini. Gunakan HTTPS atau http://localhost:8000.'
          );
        }
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: { frameRate: { ideal: 15, max: 20 } },
          audio: false,
        });
        const track = stream.getVideoTracks()[0];
        const trackLabel = track?.label || 'Browser Window Capture';
        await startBrowserPushPipeline(trackLabel, { stream });
      } else if (sourceType === 'webcam') {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error(
            'Browser tidak mengizinkan akses kamera di alamat ini. Gunakan HTTPS atau http://localhost:8000.'
          );
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' },
          audio: false,
        });
        const track = stream.getVideoTracks()[0];
        await startBrowserPushPipeline(track?.label || 'USB Camera / HDMI', { stream });
      } else if (sourceType === 'local_file') {
        if (!localFile) {
          throw new Error('Pilih file video MP4/WebM dari perangkat Anda terlebih dahulu.');
        }
        await startBrowserPushPipeline(localFile.name, { file: localFile });
      } else {
        cleanupBrowserIngest();
        let param = '';
        if (sourceType === 'testbench') param = selectedVideo;
        else if (sourceType === 'youtube') param = youtubeUrl;
        else if (sourceType === 'network') param = networkUrl;
        else if (sourceType === 'tiktok') param = tiktokUsername;

        const res = await authFetch(`/api/channels/${channelId}/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_type: sourceType,
            source_param: param,
            session_id: sessionIdRef.current,
          }),
        });
        const data = await res.json();
        if (data.success) {
          setIsStreaming(true);
        } else {
          setStreamError(data.error || 'Gagal memulai stream server.');
        }
      }
    } catch (err) {
      cleanupBrowserIngest();
      const msg = err instanceof Error ? err.message : 'Gagal memulai capture stream.';
      setStreamError(msg);
    } finally {
      setLoadingStream(false);
    }
  };

  const handleStopStream = async () => {
    setLoadingStream(true);
    try {
      if (isBrowserPush) {
        cleanupBrowserIngest();
      } else {
        await authFetch(`/api/channels/${channelId}/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionIdRef.current }),
        });
        setIsStreaming(false);
      }
    } finally {
      setLoadingStream(false);
    }
  };

  const handleReloadModel = async () => {
    const res = await authFetch('/api/system/reload-model', { method: 'POST' });
    const data = await res.json();
    if (!data.success) setStreamError(data.message);
  };

  const effectiveHeading = isStreaming ? (telemetry.heading_deg ?? 0) : 0;
  const effectiveCardinal = isStreaming ? (telemetry.cardinal ?? 'N') : 'N';
  const effectiveTurnRate = isStreaming ? (telemetry.turn_rate_dps ?? 0) : 0;

  const sourceButtons: Array<{ id: OperatorSourceType; label: string; icon: React.ComponentType<{ className?: string }> }> = [
    { id: 'window', label: 'Tangkap Window', icon: Monitor },
    { id: 'webcam', label: 'Kamera / HDMI', icon: Camera },
    { id: 'local_file', label: 'Video Laptop', icon: Upload },
    { id: 'testbench', label: 'Testbench VPS', icon: Tv },
    { id: 'network', label: 'RTSP / UDP', icon: Radio },
    { id: 'youtube', label: 'YouTube URL', icon: Film },
    { id: 'tiktok', label: 'TikTok Live', icon: Share2 },
  ];

  // Lock screen jika channel sedang dipakai operator lain
  if (lockedByOther && !hasLock) {
    return (
      <div className="h-[calc(100vh-3.5rem)] w-full bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded p-6 space-y-4 font-mono">
          <div className="flex items-center space-x-2 text-amber-400">
            <Lock className="w-5 h-5" />
            <h2 className="text-sm font-bold uppercase tracking-wider">
              Channel {channelId.toUpperCase()} Sedang Terkunci
            </h2>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Saat ini siaran <b className="text-white">{channelId.toUpperCase()}</b> sedang dikendalikan oleh{' '}
            <b className="text-signal-cyan">{lockOwnerLabel}</b>. Anda tetap bisa menonton sebagai Spectator, atau masukkan PIN untuk mengambil alih kendali.
          </p>

          {lockError && (
            <div className="text-xs text-signal-red bg-red-950/50 border border-red-800/70 px-3 py-2 rounded">
              {lockError}
            </div>
          )}

          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              claimChannel(takeoverPin);
            }}
          >
            <div className="space-y-2">
              <label htmlFor="takeover-pin" className="block text-[11px] text-slate-400">
                PIN Ambil Alih (Default: 1234):
              </label>
              <input
                id="takeover-pin"
                type="password"
                value={takeoverPin}
                onChange={(e) => setTakeoverPin(e.target.value)}
                placeholder="Masukkan PIN Operator"
                className="w-full min-h-[44px] sm:min-h-0 bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:border-signal-cyan focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <button
                type="submit"
                className="flex-1 min-h-[44px] sm:min-h-0 py-2 px-3 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan"
              >
                Ambil Alih Channel
              </button>
              <button
                type="button"
                onClick={() => claimChannel()}
                className="min-h-[44px] sm:min-h-0 py-2 px-3 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan"
              >
                Cek Status
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  const overlayW = telemetry.frame_size?.width || localVideoDims.w;
  const overlayH = telemetry.frame_size?.height || localVideoDims.h;

  return (
    <div className="flex flex-col lg:flex-row min-h-[calc(100vh-3.5rem)] lg:h-[calc(100vh-3.5rem)] w-full lg:overflow-hidden bg-slate-950">
      {/* Main Video Stage */}
      <div className="flex-1 min-h-[280px] sm:min-h-[380px] lg:min-h-0 lg:h-full flex flex-col relative overflow-hidden bg-black">
        <div className="flex-1 relative flex items-center justify-center overflow-hidden">
          <video
            ref={localVideoRef}
            muted
            playsInline
            autoPlay
            className={isBrowserPush ? 'w-full h-full object-contain pointer-events-none select-none' : 'hidden'}
          />
          {isBrowserPush ? (
            <LocalOverlayCanvas
              detections={telemetry.detections || []}
              sourceWidth={overlayW}
              sourceHeight={overlayH}
              channelId={channelId}
              showReticle={reticleVisible}
              showLabels={labelsVisible}
            />
          ) : (
            <RemoteStreamCanvas channelId={channelId} mode="main" />
          )}

          {/* Top-Left OSD Badge */}
          <div className="absolute top-3 left-3 bg-slate-900/85 border border-slate-700/70 px-2.5 py-1 rounded text-[11px] font-mono text-slate-300 flex items-center space-x-2 z-10 pointer-events-none">
            <span className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-signal-green animate-pulse' : 'bg-slate-500'}`} />
            <span className="font-semibold uppercase">
              OP {channelId === 'drone' ? 'DRONE' : 'ROV DANAU'}
            </span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400">{sourceType.toUpperCase()}</span>
          </div>

          {compassVisible && (
            <div className="hidden sm:block absolute top-3 left-1/2 -translate-x-1/2 z-10">
              <CompassRibbon heading={effectiveHeading} cardinal={effectiveCardinal} />
            </div>
          )}

          <div
            className="absolute top-3 right-3 px-2.5 py-1 rounded text-[11px] font-mono font-bold uppercase tracking-wider border z-10 pointer-events-none"
            style={{
              backgroundColor: `${telemetry.threat_color_hex}20`,
              borderColor: `${telemetry.threat_color_hex}70`,
              color: telemetry.threat_color_hex,
            }}
          >
            {telemetry.threat_level}
          </div>

          {compassVisible && (
            <div className="absolute bottom-4 right-4 z-10">
              <CircularCompassDial heading={effectiveHeading} cardinal={effectiveCardinal} />
            </div>
          )}
        </div>
      </div>

      {/* Right Operator Sidebar */}
      <div className="w-full lg:w-96 shrink-0 h-auto lg:h-full bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 flex flex-col z-20">
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
                Sumber Live Feed ({channelId.toUpperCase()}):
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {sourceButtons.map((s) => {
                  const Icon = s.icon;
                  const isSelected = sourceType === s.id;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      disabled={isStreaming}
                      onClick={() => {
                        setStreamError('');
                        setSourceType(s.id);
                      }}
                      className={`flex items-center space-x-2 px-2.5 py-2 rounded text-xs font-mono transition-colors text-left disabled:opacity-60 ${
                        isSelected
                          ? 'bg-slate-800 text-signal-cyan border border-slate-700'
                          : 'bg-slate-950 text-slate-300 hover:bg-slate-800 border border-slate-800/60'
                      }`}
                    >
                      <Icon className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-signal-cyan' : 'text-slate-500'}`} />
                      <span className="truncate">{s.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="bg-slate-950 p-3 rounded border border-slate-800 space-y-2">
              {sourceType === 'window' && (
                <p className="text-xs font-mono text-slate-300 leading-relaxed">
                  Klik <b>Mulai Siaran</b> untuk memilih jendela aplikasi (DJI, BlueOS, VLC, atau tab browser) langsung dari laptop Anda.
                </p>
              )}

              {sourceType === 'webcam' && (
                <p className="text-xs font-mono text-slate-300 leading-relaxed">
                  Menangkap input kamera laptop atau HDMI Capture Card USB yang terpasang di perangkat Anda.
                </p>
              )}

              {sourceType === 'local_file' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">
                    Pilih File Video Laptop (.mp4 / .webm):
                  </label>
                  <input
                    type="file"
                    accept="video/*"
                    onChange={(e) => setLocalFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-slate-300 font-mono file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-slate-800 file:text-signal-cyan"
                  />
                </div>
              )}

              {sourceType === 'testbench' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">Pilih Video Testbench VPS:</label>
                  <select
                    value={selectedVideo}
                    onChange={(e) => setSelectedVideo(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  >
                    {testbenchVideos.map((v) => (
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

              {sourceType === 'tiktok' && (
                <div>
                  <label className="text-[11px] font-mono text-slate-400 block mb-1">Username / URL TikTok Live:</label>
                  <input
                    type="text"
                    value={tiktokUsername}
                    onChange={(e) => setTiktokUsername(e.target.value)}
                    placeholder="@username atau URL FLV/M3U8"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                  />
                </div>
              )}
            </div>

            {streamError && (
              <div className="text-xs font-mono text-signal-red bg-red-950/40 border border-red-800/70 p-2.5 rounded">
                {streamError}
              </div>
            )}

            <div className="pt-1">
              {!isStreaming ? (
                <button
                  type="button"
                  onClick={handleStartStream}
                  disabled={loadingStream}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-bold text-xs uppercase tracking-wider transition-colors disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  <span>{loadingStream ? 'Menghubungkan...' : 'Mulai Siaran Live'}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStopStream}
                  disabled={loadingStream}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded bg-red-600 hover:bg-red-500 text-white font-mono font-bold text-xs uppercase tracking-wider transition-colors disabled:opacity-50"
                >
                  <Square className="w-4 h-4" />
                  <span>{loadingStream ? 'Menghentikan...' : 'Hentikan Siaran'}</span>
                </button>
              )}
            </div>

            {/* Statistik Live Koneksi Channel */}
            <div className="bg-slate-950 p-3 rounded border border-slate-800 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Status Channel:</span>
                <span className={isStreaming ? 'text-signal-green font-bold' : 'text-slate-500'}>
                  {isStreaming ? 'LIVE KE SPECTATOR' : 'STANDBY'}
                </span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Video / AI Speed:</span>
                <span className="text-white font-telemetry">
                  {telemetry.fps.toFixed(1)} FPS ({telemetry.ai_fps?.toFixed(1) ?? '0.0'} AI/s)
                </span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Latensi Inferensi:</span>
                <span className="text-white font-telemetry">{telemetry.latency_ms.toFixed(1)} ms</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Target Manifest */}
        {sidebarTab === 'telemetry' && (
          <div className="flex-1 overflow-y-auto p-4">
            <TargetManifestPanel
              telemetry={telemetry}
              isStreaming={isStreaming}
              effectiveHeading={effectiveHeading}
              effectiveCardinal={effectiveCardinal}
              effectiveTurnRate={effectiveTurnRate}
            />
          </div>
        )}

        {/* Tab 3: Parameter AI & Kompas */}
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
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setConfidenceGate(val);
                  updateChannelConfig({ confidence_gate: val });
                }}
                className="w-full h-1.5 bg-slate-950 rounded appearance-none cursor-pointer accent-signal-cyan"
              />
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  const nextVal = !duskEnhancer;
                  setDuskEnhancer(nextVal);
                  updateChannelConfig({ dusk_enhancer: nextVal });
                }}
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
                onClick={() => {
                  const nextVal = !reticleVisible;
                  setReticleVisible(nextVal);
                  updateChannelConfig({ reticle_visible: nextVal });
                }}
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
                onClick={() => {
                  const nextVal = !labelsVisible;
                  setLabelsVisible(nextVal);
                  updateChannelConfig({ labels_visible: nextVal });
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-mono border transition-colors ${
                  labelsVisible
                    ? 'bg-emerald-900/30 text-emerald-200 border-emerald-600/50'
                    : 'bg-slate-950 text-slate-400 border-slate-800'
                }`}
              >
                <div className="flex items-center space-x-2">
                  {labelsVisible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                  <span>Label Teks Deteksi</span>
                </div>
                <span className="font-bold">{labelsVisible ? 'ON' : 'OFF'}</span>
              </button>
            </div>

            <div className="pt-2 border-t border-slate-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-300 flex items-center space-x-1.5">
                  <Compass className="w-3.5 h-3.5 text-signal-cyan" />
                  <span>Pita Kompas Taktis</span>
                </span>
                <button
                  type="button"
                  onClick={() => setCompassVisible(!compassVisible)}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold transition-colors ${
                    compassVisible
                      ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-600/40'
                      : 'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}
                >
                  {compassVisible ? 'AKTIF' : 'NONAKTIF'}
                </button>
              </div>

              <div className="bg-slate-950 p-2.5 rounded border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-400">Kalibrasi Acuan:</span>
                  <button
                    type="button"
                    onClick={handleSetNorth}
                    disabled={calibratingCompass}
                    className="flex items-center space-x-1 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-signal-cyan text-[10px] font-mono font-semibold border border-slate-700 transition-colors disabled:opacity-50"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>SET NORTH (000°)</span>
                  </button>
                </div>

                <div>
                  <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 mb-1">
                    <span>Manual Offset:</span>
                    <span className="text-white font-telemetry">{manualOffset}°</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="359"
                    step="1"
                    value={manualOffset}
                    onChange={(e) => handleApplyOffset(parseInt(e.target.value, 10))}
                    className="w-full h-1 bg-slate-900 rounded appearance-none cursor-pointer accent-signal-cyan"
                  />
                </div>
              </div>
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
