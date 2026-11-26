import React from 'react';
import { Compass } from 'lucide-react';
import type { TelemetryData } from '../../types';

interface TargetManifestPanelProps {
  telemetry: TelemetryData;
  isStreaming: boolean;
  effectiveHeading: number;
  effectiveCardinal: string;
  effectiveTurnRate: number;
}

export const TargetManifestPanel: React.FC<TargetManifestPanelProps> = ({
  telemetry,
  isStreaming,
  effectiveHeading,
  effectiveCardinal,
  effectiveTurnRate,
}) => {
  return (
    <div className="space-y-3">
      <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono">
        <div className="flex items-center justify-between text-[10px] text-slate-400 uppercase tracking-wider">
          <span className="flex items-center space-x-1.5">
            <Compass className="w-3.5 h-3.5 text-signal-cyan" />
            <span>Orientasi Visual (Yaw)</span>
          </span>
          <span className="text-[10px] text-signal-green font-semibold">
            {!isStreaming ? 'STANDBY (0° N)' : telemetry.compass_calibrated ? 'TERKALIBRASI' : 'AKTIF'}
          </span>
        </div>
        <div className="mt-1 flex items-baseline justify-between">
          <div className="text-xl font-bold text-white font-telemetry flex items-baseline space-x-1.5">
            <span>{effectiveHeading.toFixed(1)}°</span>
            <span className="text-xs text-signal-cyan font-bold font-mono">
              {effectiveCardinal}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            Rotasi: <b className="text-slate-200">{effectiveTurnRate.toFixed(1)}°/s</b>
          </div>
        </div>
      </div>

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

      <div>
        <div className="flex justify-between items-center mb-2 text-[11px] font-mono text-slate-400 uppercase">
          <span>Daftar Target Terdeteksi:</span>
          <span>{telemetry.detections.length} Objek</span>
        </div>

        <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
          {telemetry.detections.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-500 font-mono bg-slate-950 rounded border border-slate-800/70">
              {isStreaming ? 'Tidak ada objek terdeteksi dalam frame' : 'Menunggu siaran feed aktif'}
            </div>
          ) : (
            telemetry.detections.map((det, idx) => (
              <div
                key={det.track_id ? `${det.track_id}-${idx}` : idx}
                className="bg-slate-950 p-2 rounded border border-slate-800 flex items-center justify-between text-xs font-mono"
              >
                <div className="flex items-center space-x-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: det.color_hex }}
                  />
                  <div className="truncate max-w-[140px]">
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
                      color: det.color_hex,
                    }}
                  >
                    {det.threat}
                  </span>
                  {det.estimated_distance_m != null && (
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
  );
};
