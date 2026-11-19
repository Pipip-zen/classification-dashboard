import React, { useState } from 'react';
import { Layers, Upload, Download, CheckCircle, AlertTriangle, Image as ImageIcon } from 'lucide-react';

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
      alert("Pilih minimal 2 citra foto beririsan untuk stitching");
      return;
    }
    setLoading(true);

    const formData = new FormData();
    selectedFiles.forEach((f) => formData.append('files', f));
    formData.append('mode', mode);
    formData.append('crop_borders', cropBorders ? 'true' : 'false');

    try {
      const res = await fetch('/api/stitching/stitch', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      alert("Error menghubungi server backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-aerospace-border pb-4">
        <div>
          <h1 className="text-xl font-bold font-mono text-white flex items-center space-x-2">
            <Layers className="w-5 h-5 text-tactical-cyan" />
            <span>PANORAMA IMAGE STITCHING: CITRA WIDE-ANGLE PATROLI</span>
          </h1>
          <p className="text-xs text-tactical-muted mt-1">
            Menggabungkan serangkaian citra foto beririsan (overlap &gt; 30%) dari patroli ROV dasar danau atau drone udara menjadi peta panorama terpadu.
          </p>
        </div>
      </div>

      {/* Grid Konfigurasi & Preview Input */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Kolom Kiri: Upload & Pengaturan */}
        <div className="space-y-4">
          <div className="tactical-glass p-4 rounded-xl border border-aerospace-border space-y-4">
            <h2 className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider">
              Unggah Rangkaian Citra
            </h2>

            {/* Multi Dropzone */}
            <label className="border-2 border-dashed border-aerospace-border hover:border-tactical-cyan/50 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all bg-aerospace-panel/40">
              <Upload className="w-8 h-8 text-tactical-cyan mb-2" />
              <span className="text-xs font-mono text-gray-300 text-center">
                {selectedFiles.length > 0 
                  ? `${selectedFiles.length} Berkas Citra Terpilih` 
                  : 'Pilih 2 atau lebih foto beririsan'}
              </span>
              <span className="text-[10px] text-gray-500 font-mono mt-1">Format: JPG, PNG (Multi-select)</span>
              <input type="file" multiple accept="image/*" onChange={handleFilesChange} className="hidden" />
            </label>

            {/* Mode Stitcher */}
            <div>
              <label className="text-[11px] font-mono text-gray-400 block mb-1">Mode Algoritma:</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full bg-aerospace-bg border border-aerospace-border rounded px-3 py-2 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
              >
                <option value="panorama">Panorama (Rotasi Kamera / Lensa Melengkung)</option>
                <option value="scans">Scans (Translasi Datar / Drone Mapping Planar)</option>
              </select>
            </div>

            {/* Crop Borders Toggle */}
            <div className="flex items-center justify-between p-2.5 rounded bg-aerospace-panel border border-aerospace-border">
              <span className="text-xs font-mono text-gray-300">Pangkas Batas Hitam (Trim):</span>
              <input
                type="checkbox"
                checked={cropBorders}
                onChange={(e) => setCropBorders(e.target.checked)}
                className="w-4 h-4 rounded accent-tactical-cyan cursor-pointer"
              />
            </div>

            {/* Action Button */}
            <button
              onClick={handleRunStitching}
              disabled={loading || selectedFiles.length < 2}
              className="w-full py-2.5 rounded-lg bg-tactical-cyan hover:bg-cyan-400 text-black font-mono font-bold text-xs tracking-wider transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-glow-cyan"
            >
              {loading ? 'MEMPROSES HOMOGRAFI & STITCHING...' : 'JALANKAN STITCHING PANORAMA'}
            </button>
          </div>

          {/* Thumbnail List */}
          {selectedFiles.length > 0 && (
            <div className="tactical-glass p-3 rounded-xl border border-aerospace-border">
              <div className="text-[11px] font-mono text-gray-400 uppercase mb-2">
                Daftar Foto Input ({selectedFiles.length}):
              </div>
              <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                {selectedFiles.map((f, i) => (
                  <div key={i} className="bg-aerospace-panel p-1 rounded border border-aerospace-border text-center">
                    <div className="text-[10px] text-gray-400 font-mono truncate">{f.name}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Kolom Kanan: Hasil Panorama */}
        <div className="lg:col-span-2 space-y-4">
          <div className="tactical-glass p-4 rounded-xl border border-aerospace-border">
            <div className="flex items-center justify-between mb-3 border-b border-aerospace-border pb-2">
              <h2 className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider flex items-center space-x-2">
                <ImageIcon className="w-4 h-4 text-tactical-cyan" />
                <span>HASIL CITRA PANORAMA</span>
              </h2>
              {result && result.success && (
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-mono text-tactical-emerald font-bold">
                    {result.resolution.width} x {result.resolution.height} px
                  </span>
                  <a
                    href={result.panorama_url}
                    download="tactical_panorama.jpg"
                    className="flex items-center space-x-1 px-2.5 py-1 rounded bg-tactical-cyan text-black font-mono font-bold text-xs"
                  >
                    <Download className="w-3 h-3" />
                    <span>Unduh</span>
                  </a>
                </div>
              )}
            </div>

            {/* Notification Banner */}
            {result && (
              <div 
                className={`p-3 rounded-lg mb-3 flex items-center space-x-2 font-mono text-xs border ${
                  result.success 
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' 
                    : 'bg-red-500/20 text-red-300 border-red-500/40'
                }`}
              >
                {result.success ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
                <span>{result.message}</span>
              </div>
            )}

            {/* Viewport Panorama */}
            <div className="w-full h-[450px] bg-aerospace-stage rounded-lg border border-aerospace-border flex items-center justify-center overflow-auto p-2">
              {result && result.success ? (
                <img
                  src={result.panorama_url}
                  alt="Panorama Stitched"
                  className="max-w-none h-full object-contain"
                />
              ) : (
                <div className="text-center text-gray-500 font-mono text-xs">
                  {loading ? 'Sedang melakukan feature matching SIFT/ORB & homografi matriks...' : 'Citra panorama akan ditampilkan di sini'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
