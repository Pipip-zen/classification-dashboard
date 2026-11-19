import React from 'react';
import { 
  ShieldAlert, 
  Video, 
  Database, 
  Cpu, 
  Activity
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
    { id: 'dataset', label: 'Dataset', icon: Database },
  ];

  return (
    <header className="h-14 bg-slate-900 border-b border-slate-800 px-3 lg:px-5 flex items-center justify-between select-none z-30 sticky top-0">
      {/* Brand & Cockpit Switcher */}
      <div className="flex items-center space-x-3 shrink-0">
        <div className="flex items-center space-x-2">
          <span className="font-mono font-extrabold text-sm tracking-wider text-emerald-400">
            VANGUARD
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/30 text-emerald-300 font-semibold uppercase tracking-wider">
            AI GCS
          </span>
        </div>

        {/* Cockpit Mode Toggle */}
        <div className="flex items-center bg-slate-950 p-0.5 rounded border border-slate-800">
          <button
            type="button"
            onClick={() => setCockpitMode('rov')}
            className={`px-2.5 py-1 rounded text-[11px] font-mono font-semibold transition-colors ${
              cockpitMode === 'rov'
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ROV DANAU
          </button>
          <button
            type="button"
            onClick={() => setCockpitMode('drone')}
            className={`px-2.5 py-1 rounded text-[11px] font-mono font-semibold transition-colors ${
              cockpitMode === 'drone'
                ? 'bg-emerald-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            DRONE SPECTATOR
          </button>
        </div>
      </div>

      {/* Navigation Tabs (Scrollable on small viewports) */}
      <nav className="flex items-center space-x-1 overflow-x-auto py-1 px-2 scrollbar-none">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-medium shrink-0 transition-colors ${
                isActive
                  ? 'bg-slate-800 text-white border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-signal-cyan' : 'text-slate-500'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Telemetry Status Right Pill */}
      <div className="flex items-center space-x-2 shrink-0 text-xs font-mono">
        <div className="hidden md:flex items-center space-x-1.5 bg-slate-950 px-2 py-1 rounded border border-slate-800">
          <Activity className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">FPS:</span>
          <span className="text-slate-200 font-bold font-telemetry">{telemetry.fps.toFixed(1)}</span>
        </div>
        <div className="hidden lg:flex items-center space-x-1.5 bg-slate-950 px-2 py-1 rounded border border-slate-800">
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">LAT:</span>
          <span className="text-slate-200 font-bold font-telemetry">{telemetry.latency_ms.toFixed(0)}ms</span>
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
