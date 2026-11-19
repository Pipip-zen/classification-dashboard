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
      alert("Silakan pilih gambar terlebih dahulu");
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
      alert("Error menghubungi backend");
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
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-aerospace-border pb-4">
        <div>
          <h1 className="text-xl font-bold font-mono text-white flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-tactical-cyan" />
            <span>MEDIA ANALYSIS: INSPEKSI TAKTIS CITRA OFFLINE</span>
          </h1>
          <p className="text-xs text-tactical-muted mt-1">
            Analisis presisi untuk citra foto udara Drone dan bawah air ROV dengan ekspor data terverifikasi.
          </p>
        </div>
      </div>

      {/* Grid Kontrol & Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Kolom Kiri: Input Controls */}
        <div className="space-y-4">
          <div className="tactical-glass p-4 rounded-xl border border-aerospace-border space-y-4">
            <h2 className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider">
              Unggah Berkas Citra
            </h2>

            {/* Dropzone */}
            <label className="border-2 border-dashed border-aerospace-border hover:border-tactical-cyan/50 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all bg-aerospace-panel/40">
              <Upload className="w-8 h-8 text-tactical-cyan mb-2" />
              <span className="text-xs font-mono text-gray-300 text-center">
                {selectedFile ? selectedFile.name : 'Klik atau seret gambar ke sini'}
              </span>
              <span className="text-[10px] text-gray-500 font-mono mt-1">PNG, JPG, JPEG, WebP</span>
              <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            </label>

            {/* Mode Cockpit */}
            <div>
              <label className="text-[11px] font-mono text-gray-400 block mb-1.5">Domain Taksonomi:</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setMode('drone')}
                  className={`py-2 px-3 rounded text-xs font-mono font-bold border transition-all ${
                    mode === 'drone'
                      ? 'bg-emerald-600/30 text-tactical-emerald border-tactical-emerald/50'
                      : 'bg-aerospace-panel text-gray-400 border-aerospace-border'
                  }`}
                >
                  🟢 DRONE SPECTATOR
                </button>
                <button
                  type="button"
                  onClick={() => setMode('rov')}
                  className={`py-2 px-3 rounded text-xs font-mono font-bold border transition-all ${
                    mode === 'rov'
                      ? 'bg-blue-600/30 text-tactical-cyan border-tactical-cyan/50'
                      : 'bg-aerospace-panel text-gray-400 border-aerospace-border'
                  }`}
                >
                  🔵 ROV DANAU
                </button>
              </div>
            </div>

            {/* Confidence Slider */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-[11px] font-mono text-gray-400">Confidence Gate:</span>
                <span className="text-xs font-mono font-bold text-tactical-cyan">
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
                className="w-full h-1.5 bg-aerospace-panel rounded-lg appearance-none cursor-pointer accent-tactical-cyan"
              />
            </div>

            {/* Dusk Enhancer Toggle */}
            <button
              type="button"
              onClick={() => setDuskEnhancer(!duskEnhancer)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded text-xs font-mono border transition-all ${
                duskEnhancer
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                  : 'bg-aerospace-panel/60 text-gray-400 border-aerospace-border'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Moon className="w-3.5 h-3.5" />
                <span>Dusk / Low-Light Enhancer</span>
              </div>
              <span className="font-bold">{duskEnhancer ? 'ON' : 'OFF'}</span>
            </button>

            {/* Run Button */}
            <button
              onClick={handleRunAnalysis}
              disabled={loading || !selectedFile}
              className="w-full py-2.5 rounded-lg bg-tactical-cyan hover:bg-cyan-400 text-black font-mono font-bold text-xs tracking-wider transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-glow-cyan"
            >
              {loading ? 'MEMPROSES INFERENSI AI...' : 'JALANKAN ANALISIS CITRA'}
            </button>
          </div>
        </div>

        {/* Kolom Kanan: Viewport Hasil & Telemetri */}
        <div className="lg:col-span-2 space-y-4">
          <div className="tactical-glass p-4 rounded-xl border border-aerospace-border">
            <div className="flex items-center justify-between mb-3 border-b border-aerospace-border pb-2">
              <h2 className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider flex items-center space-x-2">
                <ImageIcon className="w-4 h-4 text-tactical-cyan" />
                <span>VIEWPORT CITRA HASIL ANOTASI</span>
              </h2>
              {result && (
                <div className="flex items-center space-x-2 text-xs font-mono">
                  <span className="text-gray-400">Latensi:</span>
                  <span className="text-tactical-emerald font-bold">{result.latency_ms} ms</span>
                  <span className="text-gray-400">| Resolusi:</span>
                  <span className="text-white">{result.resolution.width}x{result.resolution.height}</span>
                </div>
              )}
            </div>

            {/* Viewport Box */}
            <div className="w-full h-[400px] bg-aerospace-stage rounded-lg border border-aerospace-border flex items-center justify-center overflow-hidden relative">
              {result ? (
                <img
                  src={result.annotated_image_url}
                  alt="Annotated Result"
                  className="max-w-full max-h-full object-contain"
                />
              ) : previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Original Preview"
                  className="max-w-full max-h-full object-contain opacity-70"
                />
              ) : (
                <div className="text-center text-gray-500 font-mono text-xs">
                  Pilih gambar dan klik "Jalankan Analisis Citra" untuk melihat anotasi taktis
                </div>
              )}
            </div>

            {/* Summary Banner jika sudah ada hasil */}
            {result && (
              <div className="mt-4 grid grid-cols-4 gap-2">
                <div 
                  className="p-2.5 rounded border text-center font-mono col-span-1"
                  style={{
                    backgroundColor: `${result.threat_summary.threat_color_hex}15`,
                    borderColor: `${result.threat_summary.threat_color_hex}60`,
                    color: result.threat_summary.threat_color_hex
                  }}
                >
                  <div className="text-[10px] uppercase">SEKTOR</div>
                  <div className="font-bold text-xs">{result.threat_summary.threat_level}</div>
                </div>
                <div className="bg-aerospace-panel p-2.5 rounded border border-aerospace-border text-center font-mono">
                  <div className="text-[10px] text-gray-400">TOTAL OBJEK</div>
                  <div className="font-bold text-white text-base">{result.threat_summary.total_objects}</div>
                </div>
                <div className="bg-aerospace-panel p-2.5 rounded border border-aerospace-border text-center font-mono">
                  <div className="text-[10px] text-tactical-red">TARGET BAHAYA</div>
                  <div className="font-bold text-tactical-red text-base">{result.threat_summary.hazard_count}</div>
                </div>
                <div className="bg-aerospace-panel p-2.5 rounded border border-aerospace-border text-center font-mono">
                  <div className="text-[10px] text-tactical-emerald">TARGET NETRAL</div>
                  <div className="font-bold text-tactical-emerald text-base">{result.threat_summary.neutral_count}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabel Rincian Deteksi & CSV Export */}
      {result && result.detections && (
        <div className="tactical-glass p-4 rounded-xl border border-aerospace-border">
          <div className="flex items-center justify-between mb-3 border-b border-aerospace-border pb-2">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-tactical-cyan" />
              <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                TABEL DETAIL DETEKSI TAKTIS ({result.detections.length} OBJEK)
              </h3>
            </div>
            <button
              onClick={downloadCSV}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-aerospace-panel hover:bg-aerospace-border text-tactical-cyan text-xs font-mono border border-tactical-cyan/40 transition-all shadow-sm"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Ekspor Log CSV</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="bg-aerospace-panel border-b border-aerospace-border text-gray-400 uppercase text-[10px]">
                  <th className="p-2">#</th>
                  <th className="p-2">Nama Target</th>
                  <th className="p-2">Tingkat Ancaman</th>
                  <th className="p-2">Confidence</th>
                  <th className="p-2">Estimasi Jarak</th>
                  <th className="p-2">Bounding Box (XYXY)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-aerospace-border">
                {result.detections.map((det: any) => (
                  <tr key={det.id} className="hover:bg-aerospace-panel/60 transition-colors">
                    <td className="p-2 text-gray-500">{det.id}</td>
                    <td className="p-2 font-semibold text-white flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: det.color_hex }} />
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
                    <td className="p-2 text-tactical-cyan">{(det.confidence * 100).toFixed(1)}%</td>
                    <td className="p-2 text-gray-300">
                      {det.estimated_distance_m ? `~${det.estimated_distance_m} m` : 'N/A'}
                    </td>
                    <td className="p-2 text-gray-400 text-[11px]">[{det.bbox.join(', ')}]</td>
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
