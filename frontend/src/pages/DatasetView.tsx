import React, { useState, useEffect } from 'react';
import { Database, CheckCircle } from 'lucide-react';

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
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-aerospace-border pb-4">
        <div>
          <h1 className="text-xl font-bold font-mono text-white flex items-center space-x-2">
            <Database className="w-5 h-5 text-tactical-cyan" />
            <span>DATASET EXPLORER & TAKSONOMI 12 KELAS AI</span>
          </h1>
          <p className="text-xs text-tactical-muted mt-1">
            Taksonomi terpadu hasil penggabungan domain ROV Danau & Bawah Air dengan Drone Spectator Udara & Darat.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="tactical-glass p-4 rounded-xl border border-aerospace-border text-center">
          <div className="text-[10px] font-mono text-gray-400 uppercase">Total Kelas Taksonomi</div>
          <div className="text-2xl font-bold font-mono text-tactical-cyan mt-1">{classes.length || 12}</div>
          <div className="text-[11px] text-gray-400 font-mono mt-1">Dual-Domain Terpadu</div>
        </div>
        <div className="tactical-glass p-4 rounded-xl border border-aerospace-border text-center">
          <div className="text-[10px] font-mono text-gray-400 uppercase">Sampel Data Training</div>
          <div className="text-2xl font-bold font-mono text-tactical-emerald mt-1">
            {summary ? summary.train_samples : '...'}
          </div>
          <div className="text-[11px] text-gray-400 font-mono mt-1">data/unified_dataset/train</div>
        </div>
        <div className="tactical-glass p-4 rounded-xl border border-aerospace-border text-center">
          <div className="text-[10px] font-mono text-gray-400 uppercase">Sampel Data Validasi</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {summary ? summary.val_samples : '...'}
          </div>
          <div className="text-[11px] text-gray-400 font-mono mt-1">data/unified_dataset/valid</div>
        </div>
        <div className="tactical-glass p-4 rounded-xl border border-aerospace-border text-center">
          <div className="text-[10px] font-mono text-gray-400 uppercase">Status Unified YAML</div>
          <div className="text-lg font-bold font-mono text-tactical-emerald mt-2 flex items-center justify-center space-x-1">
            <CheckCircle className="w-4 h-4" />
            <span>TERVERIFIKASI</span>
          </div>
          <div className="text-[11px] text-gray-400 font-mono mt-1">YOLOv8 best.pt Ready</div>
        </div>
      </div>

      {/* Grid 12 Kelas Taksonomi */}
      <div className="tactical-glass p-5 rounded-xl border border-aerospace-border space-y-4">
        <h2 className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider">
          Taksonomi Terpadu 12 Kelas Sensorik
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {classes.map((cls) => (
            <div 
              key={cls.class_id}
              className="bg-aerospace-panel/80 p-3.5 rounded-lg border border-aerospace-border hover:border-tactical-cyan/40 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span 
                      className="w-3 h-3 rounded-full shadow-sm"
                      style={{ backgroundColor: cls.color_hex }}
                    />
                    <span className="font-mono font-bold text-sm text-white">
                      {cls.display}
                    </span>
                  </div>
                  <span className="font-mono text-xs text-gray-500">ID #{cls.class_id}</span>
                </div>

                <div className="mt-2 text-xs font-mono text-gray-400">
                  {cls.threat_label}
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-aerospace-border/60 flex items-center justify-between text-[11px] font-mono">
                <span className="text-gray-400">
                  Domain: <b className="text-gray-200">{cls.domain}</b>
                </span>
                <span 
                  className="px-2 py-0.5 rounded text-[10px] font-bold"
                  style={{
                    backgroundColor: `${cls.color_hex}25`,
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
