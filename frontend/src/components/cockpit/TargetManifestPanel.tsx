import React, { useEffect, useRef, useState } from 'react';
import { Compass } from 'lucide-react';
import type { Detection, TelemetryData } from '../../types';

interface TargetManifestPanelProps {
  telemetry: TelemetryData;
  isStreaming: boolean;
  effectiveHeading: number;
  effectiveCardinal: string;
  effectiveTurnRate: number;
}

interface AggregatedTarget {
  class_id: number;
  display_name: string;
  threat: 'HAZARD' | 'NEUTRAL';
  color_hex: string;
  count: number;
  maxConfidence: number;
  nearestDistanceM: number | null;
}

const THROTTLE_MS = 600;
const HOLD_GRACE_MS = 1000;

function aggregateByClass(detections: Detection[]): AggregatedTarget[] {
  const grouped = new Map<number, AggregatedTarget>();

  for (const det of detections) {
    const existing = grouped.get(det.class_id);
    const dist = det.estimated_distance_m ?? null;

    if (!existing) {
      grouped.set(det.class_id, {
        class_id: det.class_id,
        display_name: det.display_name,
        threat: det.threat,
        color_hex: det.color_hex,
        count: 1,
        maxConfidence: det.confidence,
        nearestDistanceM: dist,
      });
      continue;
    }

    existing.count += 1;
    if (det.confidence > existing.maxConfidence) {
      existing.maxConfidence = det.confidence;
    }
    if (dist !== null && (existing.nearestDistanceM === null || dist < existing.nearestDistanceM)) {
      existing.nearestDistanceM = dist;
    }
  }

  return Array.from(grouped.values()).sort((a, b) => {
    if (a.threat !== b.threat) {
      return a.threat === 'HAZARD' ? -1 : 1;
    }
    return a.class_id - b.class_id;
  });
}

export const TargetManifestPanel: React.FC<TargetManifestPanelProps> = ({
  telemetry,
  isStreaming,
  effectiveHeading,
  effectiveCardinal,
  effectiveTurnRate,
}) => {
  const [stableTargets, setStableTargets] = useState<AggregatedTarget[]>([]);
  const latestDetectionsRef = useRef<Detection[]>(telemetry.detections);
  const heldTargetsRef = useRef<Map<number, { item: AggregatedTarget; lastSeenAt: number }>>(new Map());

  useEffect(() => {
    latestDetectionsRef.current = telemetry.detections;
  }, [telemetry.detections]);

  // Redam update UI tiap 600ms dan tahan target yang berkedip selama 1 detik agar baris stabil
  useEffect(() => {
    if (!isStreaming) {
      heldTargetsRef.current.clear();
      return;
    }

    const syncStableList = () => {
      const now = Date.now();
      const freshGroups = aggregateByClass(latestDetectionsRef.current);

      for (const grp of freshGroups) {
        heldTargetsRef.current.set(grp.class_id, { item: grp, lastSeenAt: now });
      }

      const nextList: AggregatedTarget[] = [];
      for (const [cid, entry] of heldTargetsRef.current.entries()) {
        if (now - entry.lastSeenAt <= HOLD_GRACE_MS) {
          nextList.push(entry.item);
        } else {
          heldTargetsRef.current.delete(cid);
        }
      }

      nextList.sort((a, b) => {
        if (a.threat !== b.threat) {
          return a.threat === 'HAZARD' ? -1 : 1;
        }
        return a.class_id - b.class_id;
      });

      setStableTargets(nextList);
    };

    const initTimer = setTimeout(syncStableList, 0);
    const timer = setInterval(syncStableList, THROTTLE_MS);
    return () => {
      clearTimeout(initTimer);
      clearInterval(timer);
    };
  }, [isStreaming]);

  const visibleTargets = isStreaming ? stableTargets : [];

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
          <span>{visibleTargets.length} Jenis / {telemetry.total_objects} Objek</span>
        </div>

        <div className="h-64 overflow-y-auto pr-1 space-y-1.5 bg-slate-950/50 p-1.5 rounded border border-slate-800/80">
          {visibleTargets.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
              {isStreaming ? 'Tidak ada objek terdeteksi dalam frame' : 'Menunggu siaran feed aktif'}
            </div>
          ) : (
            visibleTargets.map((item) => (
              <div
                key={item.class_id}
                className="bg-slate-950 p-2 rounded border border-slate-800 flex items-center justify-between text-xs font-mono transition-colors duration-200"
              >
                <div className="flex items-center space-x-2 min-w-0">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: item.color_hex }}
                  />
                  <div className="truncate">
                    <div className="flex items-center space-x-1.5">
                      <span className="font-semibold text-white truncate">{item.display_name}</span>
                      <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-200 text-[10px] font-bold shrink-0">
                        x{item.count}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Max Conf: {(item.maxConfidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0 ml-2">
                  <span
                    className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                    style={{
                      backgroundColor: `${item.color_hex}20`,
                      color: item.color_hex,
                    }}
                  >
                    {item.threat}
                  </span>
                  {item.nearestDistanceM !== null && (
                    <div className="text-[10px] text-signal-cyan mt-0.5 font-telemetry">
                      ~{item.nearestDistanceM}m
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
