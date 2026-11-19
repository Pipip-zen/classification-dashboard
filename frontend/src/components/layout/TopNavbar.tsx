import React from 'react';
import { 
  ShieldAlert, 
  Video, 
  Layers, 
  Scissors, 
  Database, 
  Cpu, 
  Activity,
  Compass
} from 'lucide-react';
import type { TelemetryData } from '../../types';

interface TopNavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  cockpitMode: 'drone' | 'rov';
  setCockpitMode: (mode: 'drone' | 'rov') => void;
  telemetry: TelemetryData;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  activeTab,
  setActiveTab,
  cockpitMode,
  setCockpitMode,
  telemetry,
}) => {
  const tabs = [
    { id: 'live', label: 'Live Cockpit', icon: Video },
    { id: 'analysis', label: 'Media Analysis', icon: ShieldAlert },
    { id: 'stitching', label: 'Panorama Stitching', icon: Layers },
    { id: 'inpainting', label: 'Tactical Inpainting', icon: Scissors },
    { id: 'dataset', label: 'Dataset Explorer', icon: Database },
  ];

  return (
    <header className="h-16 bg-aerospace-surface/95 border-b border-aerospace-border px-4 flex items-center justify-between select-none z-50 sticky top-0 backdrop-blur-md">
      {/* Brand & Emblem */}
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded bg-gradient-to-br from-tactical-cyan/20 to-tactical-emerald/20 border border-tactical-cyan/50 flex items-center justify-center shadow-glow-cyan">
          <Compass className="w-5 h-5 text-tactical-cyan animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-mono font-bold text-sm tracking-wider text-white">
              TACTICAL AI GCS
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              v2.0-ONLINE
            </span>
          </div>
          <p className="text-[11px] text-tactical-muted tracking-tight">
            Dual-Cockpit Ground Control Station (ROV Danau & Drone Spectator)
          </p>
        </div>
      </div>

      {/* Cockpit Mode Switcher Pill */}
      <div className="flex items-center bg-aerospace-panel p-1 rounded-lg border border-aerospace-border">
        <button
          onClick={() => setCockpitMode('rov')}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-mono font-semibold transition-all ${
            cockpitMode === 'rov'
              ? 'bg-blue-600/30 text-tactical-cyan border border-tactical-cyan/50 shadow-glow-cyan'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-tactical-cyan animate-ping" />
          <span>ROV DANAU</span>
        </button>
        <button
          onClick={() => setCockpitMode('drone')}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-mono font-semibold transition-all ${
            cockpitMode === 'drone'
              ? 'bg-emerald-600/30 text-tactical-emerald border border-tactical-emerald/50 shadow-glow-emerald'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-tactical-emerald animate-ping" />
          <span>DRONE SPECTATOR</span>
        </button>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center space-x-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? 'bg-aerospace-border text-white border border-tactical-cyan/40 shadow-sm'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-aerospace-panel/60'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-tactical-cyan' : 'text-gray-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Telemetry Status Right Pill */}
      <div className="flex items-center space-x-3 text-xs font-mono">
        <div className="flex items-center space-x-1.5 bg-aerospace-panel/80 px-2.5 py-1 rounded border border-aerospace-border">
          <Activity className="w-3.5 h-3.5 text-tactical-cyan" />
          <span className="text-gray-400">FPS:</span>
          <span className="text-tactical-cyan font-bold telemetry-num">{telemetry.fps.toFixed(1)}</span>
        </div>
        <div className="flex items-center space-x-1.5 bg-aerospace-panel/80 px-2.5 py-1 rounded border border-aerospace-border">
          <Cpu className="w-3.5 h-3.5 text-tactical-emerald" />
          <span className="text-gray-400">LAT:</span>
          <span className="text-tactical-emerald font-bold telemetry-num">{telemetry.latency_ms.toFixed(0)}ms</span>
        </div>
        <div 
          className="px-2.5 py-1 rounded border font-bold text-[11px] uppercase tracking-wider"
          style={{
            backgroundColor: `${telemetry.threat_color_hex}15`,
            borderColor: `${telemetry.threat_color_hex}60`,
            color: telemetry.threat_color_hex
          }}
        >
          {telemetry.threat_level}
        </div>
      </div>
    </header>
  );
};
