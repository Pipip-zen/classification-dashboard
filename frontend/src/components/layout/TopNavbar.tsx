import React from 'react';
import {
  ShieldAlert,
  Video,
  Database,
  Cpu,
  Activity,
  LogOut,
  Eye,
} from 'lucide-react';
import type { AuthUser, ChannelId, ChannelStatusSummary, TelemetryData } from '../../types';

interface TopNavbarProps {
  user: AuthUser;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  telemetry: TelemetryData;
  channelsStatus: Record<ChannelId, ChannelStatusSummary>;
  onLogout: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  user,
  activeTab,
  setActiveTab,
  telemetry,
  channelsStatus,
  onLogout,
}) => {
  const isSpectator = user.role === 'spectator';

  const operatorTabs = [
    { id: 'live', label: 'Live Cockpit', icon: Video },
    { id: 'analysis', label: 'Media Analysis', icon: ShieldAlert },
    { id: 'dataset', label: 'Dataset', icon: Database },
  ];

  const roleBadgeStyle =
    user.role === 'drone'
      ? 'bg-emerald-600/20 text-emerald-300 border-emerald-600/50'
      : user.role === 'rov'
        ? 'bg-blue-600/20 text-blue-300 border-blue-600/50'
        : 'bg-amber-600/20 text-amber-300 border-amber-600/50';

  const isRoleLive =
    user.role === 'spectator'
      ? channelsStatus.drone?.stream_active || channelsStatus.rov?.stream_active
      : channelsStatus[user.role]?.stream_active;

  return (
    <header className="min-h-14 bg-slate-900 border-b border-slate-800 px-2.5 lg:px-5 py-1.5 md:py-0 flex flex-wrap md:flex-nowrap items-center justify-between select-none z-30 sticky top-0 gap-2 max-w-full overflow-x-hidden">
      <div className="flex items-center space-x-2.5 shrink-0">
        <div className="flex items-center space-x-1.5">
          <span className="font-mono font-extrabold text-sm tracking-wider text-emerald-400">
            VANGUARD
          </span>
          <span className="hidden sm:inline text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/30 text-emerald-300 font-semibold uppercase tracking-wider">
            AI GCS
          </span>
        </div>

        {/* Badge Peran Terkunci */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded border text-[11px] font-mono font-bold uppercase tracking-wider ${roleBadgeStyle}`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isRoleLive ? 'bg-signal-green' : 'bg-slate-500'
            }`}
          />
          <span>{user.display_name}</span>
        </div>
      </div>

      {/* Navigation: Operator boleh Live + Analysis + Dataset; Spectator khusus Monitor */}
      {isSpectator ? (
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-amber-300">
          <Eye className="w-3.5 h-3.5" />
          <span>Spectator Monitor Mode</span>
        </div>
      ) : (
        <nav className="flex items-center space-x-1 overflow-x-auto py-0.5 px-1 scrollbar-none shrink-0">
          {operatorTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                aria-label={tab.label}
                className={`flex items-center space-x-1.5 px-2.5 min-h-[38px] md:min-h-0 py-1.5 rounded text-xs font-medium shrink-0 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan ${
                  isActive
                    ? 'bg-slate-800 text-white border border-slate-700'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-signal-cyan' : 'text-slate-500'}`} />
                <span className="hidden md:inline">{tab.label}</span>
              </button>
            );
          })}
        </nav>
      )}

      {/* Telemetry + Logout */}
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
          className="hidden sm:block px-2.5 py-1 rounded border font-bold text-[11px] uppercase tracking-wider"
          style={{
            backgroundColor: `${telemetry.threat_color_hex}15`,
            borderColor: `${telemetry.threat_color_hex}60`,
            color: telemetry.threat_color_hex,
          }}
        >
          {telemetry.threat_level}
        </div>
        <button
          type="button"
          onClick={onLogout}
          aria-label="Keluar sesi akun"
          className="flex items-center space-x-1.5 px-2.5 min-h-[38px] md:min-h-0 py-1.5 rounded bg-slate-800 hover:bg-red-900/60 hover:text-red-200 text-slate-300 border border-slate-700 text-xs font-mono font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Keluar</span>
        </button>
      </div>
    </header>
  );
};
