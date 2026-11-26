import React, { useState } from 'react';
import { Eye, EyeOff, Crosshair, Compass, ArrowLeftRight, Radio, Tv } from 'lucide-react';
import type { ChannelId, ChannelStatusSummary, TelemetryData } from '../../types';
import { CompassRibbon, CircularCompassDial } from './CompassHUD';
import { RemoteStreamCanvas } from './RemoteStreamCanvas';
import { TargetManifestPanel } from './TargetManifestPanel';

interface SpectatorViewProps {
  channelsStatus: Record<ChannelId, ChannelStatusSummary>;
  telemetryByChannel: Record<ChannelId, TelemetryData>;
}

export const SpectatorView: React.FC<SpectatorViewProps> = ({
  channelsStatus,
  telemetryByChannel,
}) => {
  const [focusedChannel, setFocusedChannel] = useState<ChannelId>('drone');
  const [compassVisible, setCompassVisible] = useState<boolean>(true);
  const [hudVisible, setHudVisible] = useState<boolean>(true);

  const secondaryChannel: ChannelId = focusedChannel === 'drone' ? 'rov' : 'drone';
  const focusedStatus = channelsStatus[focusedChannel];
  const secondaryStatus = channelsStatus[secondaryChannel];
  const activeTelemetry = telemetryByChannel[focusedChannel] || focusedStatus.telemetry;

  const isFocusedStreaming = focusedStatus?.stream_active || activeTelemetry?.stream_active || false;
  const isSecondaryStreaming = secondaryStatus?.stream_active || false;

  const effectiveHeading = isFocusedStreaming ? (activeTelemetry.heading_deg ?? 0) : 0;
  const effectiveCardinal = isFocusedStreaming ? (activeTelemetry.cardinal ?? 'N') : 'N';
  const effectiveTurnRate = isFocusedStreaming ? (activeTelemetry.turn_rate_dps ?? 0) : 0;

  const handleSwapChannel = () => {
    setFocusedChannel(secondaryChannel);
  };

  return (
    <div className="flex flex-col lg:flex-row min-h-[calc(100vh-3.5rem)] lg:h-[calc(100vh-3.5rem)] w-full lg:overflow-hidden bg-slate-950">
      {/* Main Stage Spectator */}
      <div className="flex-1 min-h-[300px] sm:min-h-[400px] lg:min-h-0 lg:h-full flex flex-col relative overflow-hidden bg-black">
        {/* Quick Switch Bar di atas stage agar tidak menabrak Compass Ribbon */}
        <div className="h-11 bg-slate-900 border-b border-slate-800 px-3 flex items-center justify-between gap-2 z-20 shrink-0">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 hidden sm:inline">
              Monitor Channel:
            </span>
            <div className="flex items-center bg-slate-950 p-0.5 rounded border border-slate-800">
              {(['drone', 'rov'] as ChannelId[]).map((cid) => {
                const isActive = focusedChannel === cid;
                const isLive = channelsStatus[cid]?.stream_active;
                return (
                  <button
                    key={cid}
                    type="button"
                    onClick={() => setFocusedChannel(cid)}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan ${
                      isActive
                        ? cid === 'drone'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        isLive ? 'bg-signal-green animate-pulse' : 'bg-slate-600'
                      }`}
                    />
                    <span>{cid === 'drone' ? 'DRONE' : 'ROV DANAU'}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center space-x-2 text-[11px] font-mono">
            <span className="hidden md:inline text-slate-400">
              {focusedStatus?.owner_label ? `Op: ${focusedStatus.owner_label}` : 'Belum ada Operator'}
            </span>
            <span
              className="px-2 py-0.5 rounded font-bold uppercase border"
              style={{
                backgroundColor: `${activeTelemetry.threat_color_hex}20`,
                borderColor: `${activeTelemetry.threat_color_hex}70`,
                color: activeTelemetry.threat_color_hex,
              }}
            >
              {activeTelemetry.threat_level}
            </span>
          </div>
        </div>

        {/* Video Viewport */}
        <div className="flex-1 relative flex items-center justify-center overflow-hidden">
          <RemoteStreamCanvas channelId={focusedChannel} mode="main" />

          {hudVisible && (
            <div className="absolute top-3 left-3 bg-slate-900/85 border border-slate-700/70 px-2.5 py-1 rounded text-[11px] font-mono text-slate-200 flex items-center space-x-2 z-10 pointer-events-none">
              <span className={`w-2 h-2 rounded-full ${isFocusedStreaming ? 'bg-signal-green' : 'bg-slate-500'}`} />
              <span className="font-semibold uppercase">
                {focusedChannel === 'drone' ? 'FEED DRONE' : 'FEED ROV'}
              </span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-300 font-telemetry">{activeTelemetry.fps.toFixed(1)} FPS</span>
            </div>
          )}

          {compassVisible && hudVisible && (
            <div className="hidden sm:block absolute top-3 left-1/2 -translate-x-1/2 z-10">
              <CompassRibbon heading={effectiveHeading} cardinal={effectiveCardinal} />
            </div>
          )}

          {compassVisible && hudVisible && (
            <div className="absolute bottom-4 left-4 z-10">
              <CircularCompassDial heading={effectiveHeading} cardinal={effectiveCardinal} />
            </div>
          )}

          {/* Mini Preview (PiP) Channel Kedua untuk Switch Instan */}
          <button
            type="button"
            onClick={handleSwapChannel}
            aria-label={`Tukar tampilan ke channel ${secondaryChannel.toUpperCase()}`}
            className="group absolute bottom-3 right-3 sm:bottom-4 sm:right-4 z-20 w-36 sm:w-56 bg-slate-950 border border-slate-700 hover:border-signal-cyan rounded overflow-hidden shadow-2xl text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan"
          >
            <div className="px-2 py-1 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-[10px] font-mono">
              <span className="flex items-center space-x-1.5 font-semibold text-slate-200">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isSecondaryStreaming ? 'bg-signal-green animate-pulse' : 'bg-slate-500'
                  }`}
                />
                <span>{secondaryChannel === 'drone' ? 'DRONE' : 'ROV DANAU'}</span>
              </span>
              <span className="flex items-center space-x-1 text-signal-cyan group-hover:underline">
                <ArrowLeftRight className="w-3 h-3" />
                <span>Switch</span>
              </span>
            </div>
            <div className="aspect-video w-full bg-black relative">
              <RemoteStreamCanvas
                channelId={secondaryChannel}
                mode="pip"
                className="w-full h-full object-cover pointer-events-none"
              />
            </div>
          </button>
        </div>
      </div>

      {/* Right Sidebar Spectator (Read-Only) */}
      <aside className="w-full lg:w-96 shrink-0 h-auto lg:h-full bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 flex flex-col z-20 overflow-y-auto p-4 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
          <div className="flex items-center space-x-2">
            <Tv className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
              Spectator Monitor (Read-Only)
            </span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            LIVE SYNC
          </span>
        </div>

        {/* Ringkasan Status Kedua Channel */}
        <div className="grid grid-cols-2 gap-2">
          {(['drone', 'rov'] as ChannelId[]).map((cid) => {
            const st = channelsStatus[cid];
            const tel = telemetryByChannel[cid] || st.telemetry;
            const selected = focusedChannel === cid;
            return (
              <button
                key={cid}
                type="button"
                onClick={() => setFocusedChannel(cid)}
                className={`p-2.5 rounded border text-left font-mono transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan ${
                  selected
                    ? 'bg-slate-800 border-signal-cyan text-white'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center justify-between text-[11px] font-bold">
                  <span>{cid === 'drone' ? 'DRONE' : 'ROV DANAU'}</span>
                  <Radio
                    className={`w-3.5 h-3.5 ${
                      st.stream_active ? 'text-signal-green' : 'text-slate-600'
                    }`}
                  />
                </div>
                <div className="mt-1 text-[10px] text-slate-400">
                  {st.stream_active ? `${tel.fps.toFixed(0)} FPS | ${tel.latency_ms.toFixed(0)}ms` : 'STANDBY'}
                </div>
                <div className="mt-0.5 text-[10px]" style={{ color: tel.threat_color_hex }}>
                  {tel.total_objects} Target ({tel.hazard_count} Bahaya)
                </div>
              </button>
            );
          })}
        </div>

        {/* Target Manifest Channel Terfokus */}
        <TargetManifestPanel
          telemetry={activeTelemetry}
          isStreaming={isFocusedStreaming}
          effectiveHeading={effectiveHeading}
          effectiveCardinal={effectiveCardinal}
          effectiveTurnRate={effectiveTurnRate}
        />

        {/* Filter HUD Lokal Spectator */}
        <div className="pt-3 border-t border-slate-800 space-y-2">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
            Tampilan HUD Layar Spectator
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setHudVisible(!hudVisible)}
              className={`flex items-center justify-center space-x-1.5 py-2 px-2 rounded text-xs font-mono border transition-colors ${
                hudVisible
                  ? 'bg-slate-800 text-white border-slate-600'
                  : 'bg-slate-950 text-slate-400 border-slate-800'
              }`}
            >
              {hudVisible ? <Eye className="w-3.5 h-3.5 text-signal-cyan" /> : <EyeOff className="w-3.5 h-3.5" />}
              <span>OSD HUD</span>
            </button>

            <button
              type="button"
              onClick={() => setCompassVisible(!compassVisible)}
              className={`flex items-center justify-center space-x-1.5 py-2 px-2 rounded text-xs font-mono border transition-colors ${
                compassVisible
                  ? 'bg-slate-800 text-white border-slate-600'
                  : 'bg-slate-950 text-slate-400 border-slate-800'
              }`}
            >
              <Compass className="w-3.5 h-3.5 text-signal-cyan" />
              <span>Kompas</span>
            </button>
          </div>
          <p className="text-[10px] font-mono text-slate-500 flex items-center space-x-1">
            <Crosshair className="w-3 h-3 shrink-0" />
            <span>Parameter AI dan kompas diatur oleh masing-masing Operator.</span>
          </p>
        </div>
      </aside>
    </div>
  );
};
