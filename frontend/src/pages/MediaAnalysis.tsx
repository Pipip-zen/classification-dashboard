import React, { useState } from 'react';
import { Upload, Download, Moon, ShieldAlert, FileText, Image as ImageIcon } from 'lucide-react';

export const MediaAnalysis: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [mode, setMode] = useState<'drone' | 'rov'>('drone');
  const [confidenceGate, setConfidenceGate] = useState<number>(0.25);
  const [duskEnhancer, setDuskEnhancer] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setSelectedFile(f);
      setPreviewUrl(URL.createObjectURL(f));
      setResult(null);
    }
  };

  const handleRunAnalysis = async () => {
    if (!selectedFile) {
      alert("Pilih berkas gambar terlebih dahulu.");
      return;
    }
    setLoading(true);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('mode', mode);
    formData.append('confidence_gate', confidenceGate.toString());
    formData.append('dusk_enhancer', duskEnhancer ? 'true' : 'false');

    try {
      const res = await fetch('/api/analysis/image', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        setResult(data);
      } else {
        alert(data.detail || "Gagal melakukan analisis citra");
      }
    } catch (e) {
      alert("Gagal menghubungi server backend.");
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = () => {
    if (!result || !result.detections || result.detections.length === 0) return;
    const headers = ["ID", "Kelas", "Display Name", "Confidence", "Threat", "Threat Label", "Est Distance (m)"];
    const rows = result.detections.map((d: any) => [
      d.id,
      d.class_name,
      `"${d.display_name}"`,
      d.confidence,
      d.threat,
      `"${d.threat_label}"`,
      d.estimated_distance_m || "N/A"
    ]);

    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map((e: any[]) => e.join(","))].join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `tactical_analysis_${result.filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-5">
      {/* Page Header */}
      <div className="border-b border-slate-800 pb-3">
        <h1 className="text-lg font-bold font-mono text-slate-100 flex items-center space-x-2">
          <ShieldAlert className="w-5 h-5 text-signal-cyan" />
          <span>MEDIA ANALYSIS: INSPEKSI CITRA OFFLINE</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Pemeriksaan taktis citra foto udara dan bawah air dengan klasifikasi objek dan estimasi jarak.
        </p>
      </div>

      {/* 2-Column Workstation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Kolom Input Controls */}
        <div className="space-y-4">
          <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              Unggah Berkas Citra
            </h2>

            <label className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded p-5 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950">
              <Upload className="w-6 h-6 text-slate-400 mb-2" />
              <span className="text-xs font-mono text-slate-300 text-center">
                {selectedFile ? selectedFile.name : 'Pilih atau seret gambar ke sini'}
              </span>
              <span className="text-[10px] text-slate-500 font-mono mt-1">PNG, JPG, WebP</span>
              <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            </label>

            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">Domain Taksonomi:</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setMode('drone')}
                  className={`py-2 px-3 rounded text-xs font-mono font-bold border transition-colors ${
                    mode === 'drone'
                      ? 'bg-emerald-600/30 text-emerald-300 border-emerald-500/50'
                      : 'bg-slate-950 text-slate-400 border-slate-800'
                  }`}
                >
                  DRONE SPECTATOR
                </button>
                <button
                  type="button"
                  onClick={() => setMode('rov')}
                  className={`py-2 px-3 rounded text-xs font-mono font-bold border transition-colors ${
                    mode === 'rov'
                      ? 'bg-blue-600/30 text-blue-300 border-blue-500/50'
                      : 'bg-slate-950 text-slate-400 border-slate-800'
                  }`}
                >
                  ROV DANAU
                </button>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1 text-xs font-mono">
                <span className="text-slate-400">Confidence Gate:</span>
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
                onChange={(e) => setConfidenceGate(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-950 rounded appearance-none cursor-pointer accent-signal-cyan"
              />
            </div>

            <button
              type="button"
              onClick={() => setDuskEnhancer(!duskEnhancer)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded text-xs font-mono border transition-colors ${
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
              onClick={handleRunAnalysis}
              disabled={loading || !selectedFile}
              className="w-full py-2.5 rounded bg-signal-cyan hover:bg-cyan-500 text-slate-950 font-mono font-bold text-xs tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? 'MEMPROSES INFERENSI...' : 'JALANKAN ANALISIS CITRA'}
            </button>
          </div>
        </div>

        {/* Kolom Viewport Hasil */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900 p-4 rounded border border-slate-800">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
              <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                <ImageIcon className="w-4 h-4 text-signal-cyan" />
                <span>VIEWPORT HASIL ANOTASI</span>
              </h2>
              {result && (
                <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
                  <span>Latensi: <b className="text-emerald-400 font-telemetry">{result.latency_ms}ms</b></span>
                  <span>|</span>
                  <span>Resolusi: {result.resolution.width}x{result.resolution.height}</span>
                </div>
              )}
            </div>

            <div className="w-full h-[400px] bg-slate-950 rounded border border-slate-800 flex items-center justify-center overflow-hidden">
              {result ? (
                <img
                  src={result.annotated_image_url}
                  alt="Hasil Anotasi Taktis"
                  className="max-w-full max-h-full object-contain"
                />
              ) : previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Preview Mentah"
                  className="max-w-full max-h-full object-contain opacity-75"
                />
              ) : (
                <div className="text-center text-slate-500 font-mono text-xs">
                  Pilih gambar dan klik "JALANKAN ANALISIS CITRA"
                </div>
              )}
            </div>

            {result && (
              <div className="mt-4 grid grid-cols-4 gap-2 text-center font-mono">
                <div 
                  className="p-2 rounded border"
                  style={{
                    backgroundColor: `${result.threat_summary.threat_color_hex}15`,
                    borderColor: `${result.threat_summary.threat_color_hex}50`,
                    color: result.threat_summary.threat_color_hex
                  }}
                >
                  <div className="text-[10px] uppercase">SEKTOR</div>
                  <div className="font-bold text-xs">{result.threat_summary.threat_level}</div>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">TOTAL</div>
                  <div className="font-bold text-white text-base font-telemetry">{result.threat_summary.total_objects}</div>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-signal-red">BAHAYA</div>
                  <div className="font-bold text-signal-red text-base font-telemetry">{result.threat_summary.hazard_count}</div>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-signal-green">NETRAL</div>
                  <div className="font-bold text-signal-green text-base font-telemetry">{result.threat_summary.neutral_count}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabel Detail Deteksi */}
      {result && result.detections && (
        <div className="bg-slate-900 p-4 rounded border border-slate-800">
          <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-signal-cyan" />
              <h3 className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">
                RINCIAN TARGET ({result.detections.length} OBJEK)
              </h3>
            </div>
            <button
              type="button"
              onClick={downloadCSV}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-signal-cyan text-xs font-mono border border-slate-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Ekspor CSV</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="p-2">#</th>
                  <th className="p-2">Nama Target</th>
                  <th className="p-2">Tingkat Ancaman</th>
                  <th className="p-2">Confidence</th>
                  <th className="p-2">Estimasi Jarak</th>
                  <th className="p-2">Bounding Box</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {result.detections.map((det: any) => (
                  <tr key={det.id} className="hover:bg-slate-850 transition-colors">
                    <td className="p-2 text-slate-500 font-telemetry">{det.id}</td>
                    <td className="p-2 font-semibold text-white flex items-center space-x-2">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: det.color_hex }} />
                      <span>{det.display_name}</span>
                    </td>
                    <td className="p-2">
                      <span 
                        className="px-2 py-0.5 rounded text-[10px] font-bold"
                        style={{
                          backgroundColor: `${det.color_hex}20`,
                          color: det.color_hex
                        }}
                      >
                        {det.threat_label}
                      </span>
                    </td>
                    <td className="p-2 text-signal-cyan font-telemetry">{(det.confidence * 100).toFixed(1)}%</td>
                    <td className="p-2 text-slate-300 font-telemetry">
                      {det.estimated_distance_m ? `~${det.estimated_distance_m} m` : 'N/A'}
                    </td>
                    <td className="p-2 text-slate-400 text-[11px] font-telemetry">[{det.bbox.join(', ')}]</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
