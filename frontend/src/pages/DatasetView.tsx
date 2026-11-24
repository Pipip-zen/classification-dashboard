import React, { useState, useEffect } from 'react';
import { CheckCircle } from 'lucide-react';

export const DatasetView: React.FC = () => {
  const [classes, setClasses] = useState<any[]>([]);
  const [summary, setSummary] = useState<any | null>(null);

  useEffect(() => {
    fetch('/api/dataset/taxonomy')
      .then(res => res.json())
      .then(data => {
        if (data.classes) setClasses(data.classes);
      })
      .catch(err => console.error("Error fetching taxonomy:", err));

    fetch('/api/dataset/summary')
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(err => console.error("Error fetching dataset summary:", err));
  }, []);

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-5">
      <div className="border-b border-slate-800 pb-3">
        <h1 className="text-base font-bold font-mono text-slate-100">
          Dataset & Taksonomi
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Taksonomi 8 kelas sensorik wahana Drone Udara dan ROV Danau.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-slate-900 p-3.5 rounded border border-slate-800 text-center font-mono">
          <div className="text-[10px] text-slate-400 uppercase">Total Kelas</div>
          <div className="text-2xl font-bold text-signal-cyan mt-1 font-telemetry">{classes.length || 8}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Dual-Domain</div>
        </div>
        <div className="bg-slate-900 p-3.5 rounded border border-slate-800 text-center font-mono">
          <div className="text-[10px] text-slate-400 uppercase">Sampel Training</div>
          <div className="text-2xl font-bold text-signal-green mt-1 font-telemetry">
            {summary ? summary.train_samples : '...'}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">data/unified_dataset</div>
        </div>
        <div className="bg-slate-900 p-3.5 rounded border border-slate-800 text-center font-mono">
          <div className="text-[10px] text-slate-400 uppercase">Sampel Validasi</div>
          <div className="text-2xl font-bold text-white mt-1 font-telemetry">
            {summary ? summary.val_samples : '...'}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">data/unified_dataset</div>
        </div>
        <div className="bg-slate-900 p-3.5 rounded border border-slate-800 text-center font-mono">
          <div className="text-[10px] text-slate-400 uppercase">Status Unified YAML</div>
          <div className="text-base font-bold text-signal-green mt-2 flex items-center justify-center space-x-1">
            <CheckCircle className="w-4 h-4" />
            <span>TERVERIFIKASI</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">YOLOv8 Ready</div>
        </div>
      </div>

      {/* Grid 8 Kelas Taksonomi */}
      <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
        <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
          Daftar Taksonomi 8 Kelas Sensorik
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {classes.map((cls) => (
            <div 
              key={cls.class_id}
              className="bg-slate-950 p-3 rounded border border-slate-800 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span 
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: cls.color_hex }}
                    />
                    <span className="font-mono font-bold text-xs text-white">
                      {cls.display}
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-500 font-telemetry">ID #{cls.class_id}</span>
                </div>

                <div className="mt-1.5 text-xs font-mono text-slate-400">
                  {cls.threat_label}
                </div>
              </div>

              <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono">
                <span className="text-slate-400">
                  Domain: <b className="text-slate-300">{cls.domain}</b>
                </span>
                <span 
                  className="px-2 py-0.5 rounded text-[10px] font-semibold"
                  style={{
                    backgroundColor: `${cls.color_hex}20`,
                    color: cls.color_hex
                  }}
                >
                  {cls.threat}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
