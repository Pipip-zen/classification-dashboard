import React, { useState } from 'react';
import { Upload, Download, CheckCircle, AlertTriangle, Image as ImageIcon } from 'lucide-react';
import { authFetch } from '../utils/auth';

export const StitchingView: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [mode, setMode] = useState<string>('panorama');
  const [cropBorders, setCropBorders] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);

  const handleFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles(filesArray);
      setResult(null);
    }
  };

  const handleRunStitching = async () => {
    if (selectedFiles.length < 2) {
      alert("Pilih minimal 2 citra foto beririsan untuk proses stitching.");
      return;
    }
    setLoading(true);

    const formData = new FormData();
    selectedFiles.forEach((f) => formData.append('files', f));
    formData.append('mode', mode);
    formData.append('crop_borders', cropBorders ? 'true' : 'false');

    try {
      const res = await authFetch('/api/stitching/stitch', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch {
      alert("Gagal menghubungi server backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-5">
      {/* Page Header */}
      <div className="border-b border-slate-800 pb-3">
        <h1 className="text-base font-bold font-mono text-slate-100">
          Panorama Stitching
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Penggabungan rangkaian citra beririsan (overlap &gt; 30%) menjadi bidang pandang lebar.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Kolom Upload */}
        <div className="space-y-4">
          <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              Unggah Rangkaian Foto
            </h2>

            <label className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded p-5 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950">
              <Upload className="w-6 h-6 text-slate-400 mb-2" />
              <span className="text-xs font-mono text-slate-300 text-center">
                {selectedFiles.length > 0 
                  ? `${selectedFiles.length} berkas foto terpilih` 
                  : 'Pilih 2 atau lebih foto berurutan'}
              </span>
              <span className="text-[10px] text-slate-500 font-mono mt-1">Format: JPG, PNG</span>
              <input type="file" multiple accept="image/*" onChange={handleFilesChange} className="hidden" />
            </label>

            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">Mode Algoritma:</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
              >
                <option value="panorama">Panorama (Rotasi Kamera / Lensa Melengkung)</option>
                <option value="scans">Scans (Translasi Datar / Drone Mapping Planar)</option>
              </select>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded bg-slate-950 border border-slate-800">
              <span className="text-xs font-mono text-slate-300">Pangkas Batas Hitam:</span>
              <input
                type="checkbox"
                checked={cropBorders}
                onChange={(e) => setCropBorders(e.target.checked)}
                className="w-4 h-4 rounded accent-signal-cyan cursor-pointer"
              />
            </div>

            <button
              type="button"
              onClick={handleRunStitching}
              disabled={loading || selectedFiles.length < 2}
              className="w-full py-2.5 rounded bg-signal-cyan hover:bg-cyan-500 text-slate-950 font-mono font-bold text-xs tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? 'MEMPROSES HOMOGRAFI...' : 'JALANKAN STITCHING PANORAMA'}
            </button>
          </div>

          {selectedFiles.length > 0 && (
            <div className="bg-slate-900 p-3 rounded border border-slate-800">
              <div className="text-[11px] font-mono text-slate-400 uppercase mb-2">
                Foto Input Terpilih ({selectedFiles.length}):
              </div>
              <div className="grid grid-cols-2 gap-1.5 max-h-40 overflow-y-auto">
                {selectedFiles.map((f, i) => (
                  <div key={i} className="bg-slate-950 p-1.5 rounded border border-slate-800 text-[11px] font-mono text-slate-300 truncate">
                    {f.name}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Kolom Viewport Panorama */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900 p-4 rounded border border-slate-800">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
              <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                <ImageIcon className="w-4 h-4 text-signal-cyan" />
                <span>HASIL CITRA PANORAMA</span>
              </h2>
              {result && result.success && (
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-mono text-emerald-400 font-bold font-telemetry">
                    {result.resolution.width} x {result.resolution.height} px
                  </span>
                  <a
                    href={result.panorama_url}
                    download="tactical_panorama.jpg"
                    className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-signal-cyan font-mono text-xs border border-slate-700"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Unduh</span>
                  </a>
                </div>
              )}
            </div>

            {result && (
              <div 
                className={`p-2.5 rounded mb-3 flex items-center space-x-2 font-mono text-xs border ${
                  result.success 
                    ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800' 
                    : 'bg-red-950/40 text-red-300 border-red-800'
                }`}
              >
                {result.success ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
                <span>{result.message}</span>
              </div>
            )}

            <div className="w-full h-[440px] bg-slate-950 rounded border border-slate-800 flex items-center justify-center overflow-auto p-2">
              {result && result.success ? (
                <img
                  src={result.panorama_url}
                  alt="Panorama Hasil Stitching"
                  className="max-w-none h-full object-contain"
                />
              ) : (
                <div className="text-center text-slate-500 font-mono text-xs">
                  {loading ? 'Menghitung fitur titik temu SIFT dan estimasi homografi...' : 'Pilih minimal 2 citra dan klik jalankan stitching.'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
