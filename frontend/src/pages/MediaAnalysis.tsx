import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  Download, 
  Moon, 
  FileText, 
  Image as ImageIcon, 
  Film, 
  Clock, 
  Play 
} from 'lucide-react';

interface MediaSampleList {
  images: string[];
  videos: string[];
}

export const MediaAnalysis: React.FC = () => {
  const [activeMediaTab, setActiveMediaTab] = useState<'image' | 'video'>('image');
  
  // Sample files from server
  const [samples, setSamples] = useState<MediaSampleList>({ images: [], videos: [] });
  const [chosenImageSample, setChosenImageSample] = useState<string>('');
  const [chosenVideoSample, setChosenVideoSample] = useState<string>('');

  // Image State
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [imageResult, setImageResult] = useState<any | null>(null);

  // Video State
  const [selectedVideoFile, setSelectedVideoFile] = useState<File | null>(null);
  const [videoSamplingInterval, setVideoSamplingInterval] = useState<number>(10);
  const [videoResult, setVideoResult] = useState<any | null>(null);

  // Common Controls
  const [mode, setMode] = useState<'drone' | 'rov'>('drone');
  const [confidenceGate, setConfidenceGate] = useState<number>(0.25);
  const [duskEnhancer, setDuskEnhancer] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch sample media from server on mount
  useEffect(() => {
    fetch('/api/analysis/samples')
      .then(res => res.json())
      .then(data => {
        if (data.images || data.videos) {
          setSamples({
            images: data.images || [],
            videos: data.videos || []
          });
          if (data.images && data.images.length > 0) {
            setChosenImageSample(data.images[0]);
          }
          if (data.videos && data.videos.length > 0) {
            setChosenVideoSample(data.videos[0]);
          }
        }
      })
      .catch(() => {});
  }, []);

  const handleImageFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setSelectedImageFile(f);
      setImagePreviewUrl(URL.createObjectURL(f));
      setChosenImageSample('');
      setImageResult(null);
    }
  };

  const handleVideoFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setSelectedVideoFile(f);
      setChosenVideoSample('');
      setVideoResult(null);
    }
  };

  const handleRunImageAnalysis = async () => {
    if (!selectedImageFile && !chosenImageSample) {
      alert("Pilih atau unggah berkas foto terlebih dahulu.");
      return;
    }
    setLoading(true);
    setImageResult(null);

    const formData = new FormData();
    if (selectedImageFile) {
      formData.append('file', selectedImageFile);
    } else {
      formData.append('sample_filename', chosenImageSample);
    }
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
        setImageResult(data);
      } else {
        alert(data.detail || "Gagal melakukan analisis citra");
      }
    } catch {
      alert("Gagal menghubungi server backend.");
    } finally {
      setLoading(false);
    }
  };

  const handleRunVideoAnalysis = async () => {
    if (!selectedVideoFile && !chosenVideoSample) {
      alert("Pilih atau unggah berkas video terlebih dahulu.");
      return;
    }
    setLoading(true);
    setVideoResult(null);

    const formData = new FormData();
    if (selectedVideoFile) {
      formData.append('file', selectedVideoFile);
    } else {
      formData.append('sample_filename', chosenVideoSample);
    }
    formData.append('mode', mode);
    formData.append('confidence_gate', confidenceGate.toString());
    formData.append('dusk_enhancer', duskEnhancer ? 'true' : 'false');
    formData.append('sampling_interval', videoSamplingInterval.toString());
    formData.append('max_frames', '250');

    try {
      const res = await fetch('/api/analysis/video', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        setVideoResult(data);
      } else {
        alert(data.detail || "Gagal melakukan analisis video");
      }
    } catch {
      alert("Gagal menghubungi server backend.");
    } finally {
      setLoading(false);
    }
  };

  const downloadImageCSV = () => {
    if (!imageResult?.detections?.length) return;
    const headers = ["ID", "Kelas", "Display Name", "Confidence", "Threat", "Threat Label", "Est Distance (m)"];
    const rows = imageResult.detections.map((d: any) => [
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
    link.setAttribute("download", `image_analysis_${imageResult.filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadVideoCSV = () => {
    if (!videoResult?.detection_log?.length) return;
    const headers = ["Frame", "Timestamp (s)", "Kelas", "Target", "Confidence", "Status Ancaman", "Keterangan"];
    const rows = videoResult.detection_log.map((d: any) => [
      d.frame,
      d.timestamp_s,
      d.class_name,
      `"${d.display_name}"`,
      d.confidence,
      d.threat,
      `"${d.threat_label}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map((e: any[]) => e.join(","))].join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `video_analysis_${videoResult.filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-3 gap-2">
        <div>
          <h1 className="text-base font-bold font-mono text-slate-100">
            Media Analysis
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Inspeksi taktis berkas offline (Foto & Rekaman Video MP4) dengan deteksi YOLOv8 dan telemetri ancaman.
          </p>
        </div>

        {/* Media Type Switcher: Foto vs Video */}
        <div className="flex items-center bg-slate-900 p-0.5 rounded border border-slate-800 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveMediaTab('image')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium transition-colors ${
              activeMediaTab === 'image'
                ? 'bg-slate-800 text-white border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ImageIcon className="w-3.5 h-3.5" />
            <span>Foto Tunggal</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMediaTab('video')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium transition-colors ${
              activeMediaTab === 'video'
                ? 'bg-slate-800 text-white border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            <span>Video Rekaman (MP4)</span>
          </button>
        </div>
      </div>

      {/* 2-Column Workstation Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Kolom Kiri: Input & Parameters */}
        <div className="space-y-4">
          {/* File Selection Card */}
          <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              {activeMediaTab === 'image' ? 'Berkas Citra (Foto)' : 'Berkas Video (MP4 / AVI)'}
            </h2>

            {activeMediaTab === 'image' ? (
              <div className="space-y-3">
                <label className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded p-4 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950">
                  <Upload className="w-5 h-5 text-slate-400 mb-1" />
                  <span className="text-xs font-mono text-slate-300">
                    {selectedImageFile ? selectedImageFile.name : 'Upload Foto Baru (PNG, JPG, WebP)'}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Klik untuk memilih berkas dari komputer</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageFileChange}
                    className="hidden"
                  />
                </label>

                {samples.images.length > 0 && (
                  <div>
                    <label className="text-[11px] font-mono text-slate-400 block mb-1">
                      Atau Pilih Foto Sampel Uji:
                    </label>
                    <select
                      value={chosenImageSample}
                      onChange={(e) => {
                        setChosenImageSample(e.target.value);
                        setSelectedImageFile(null);
                        setImagePreviewUrl(null);
                        setImageResult(null);
                      }}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                    >
                      <option value="">-- Pilih Sampel Testbench --</option>
                      {samples.images.map(imgName => (
                        <option key={imgName} value={imgName}>{imgName}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <label className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded p-4 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950">
                  <Film className="w-5 h-5 text-slate-400 mb-1" />
                  <span className="text-xs font-mono text-slate-300">
                    {selectedVideoFile ? selectedVideoFile.name : 'Upload Video Rekaman (MP4, AVI)'}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Mendukung berkas rekaman drone & patroli ROV</span>
                  <input
                    type="file"
                    accept="video/mp4,video/avi,video/quicktime"
                    onChange={handleVideoFileChange}
                    className="hidden"
                  />
                </label>

                {samples.videos.length > 0 && (
                  <div>
                    <label className="text-[11px] font-mono text-slate-400 block mb-1">
                      Atau Pilih Video Sampel Testbench:
                    </label>
                    <select
                      value={chosenVideoSample}
                      onChange={(e) => {
                        setChosenVideoSample(e.target.value);
                        setSelectedVideoFile(null);
                        setVideoResult(null);
                      }}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
                    >
                      <option value="">-- Pilih Sampel Testbench --</option>
                      {samples.videos.map(vidName => (
                        <option key={vidName} value={vidName}>{vidName}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <div className="flex items-center justify-between text-xs font-mono mb-1">
                    <span className="text-slate-400">Interval Sampling:</span>
                    <span className="text-white font-bold">Tiap {videoSamplingInterval} Frame</span>
                  </div>
                  <input
                    type="range"
                    min="2"
                    max="30"
                    step="2"
                    value={videoSamplingInterval}
                    onChange={(e) => setVideoSamplingInterval(parseInt(e.target.value))}
                    className="w-full accent-emerald-500 cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-0.5">
                    <span>2 Frame (Rapat)</span>
                    <span>15 Frame</span>
                    <span>30 Frame (~1 detik)</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Configuration Card */}
          <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-4">
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              Parameter Klasifikasi
            </h2>

            {/* Mode Wahana */}
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">Domain Wahana:</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setMode('drone')}
                  className={`py-1.5 rounded text-xs font-mono font-semibold transition-colors ${
                    mode === 'drone'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  DRONE SPECTATOR
                </button>
                <button
                  type="button"
                  onClick={() => setMode('rov')}
                  className={`py-1.5 rounded text-xs font-mono font-semibold transition-colors ${
                    mode === 'rov'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  ROV DANAU
                </button>
              </div>
            </div>

            {/* Confidence Gate */}
            <div>
              <div className="flex items-center justify-between text-xs font-mono mb-1">
                <span className="text-slate-400">Ambang Batas (Confidence):</span>
                <span className="text-white font-bold">{Math.round(confidenceGate * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.85"
                step="0.05"
                value={confidenceGate}
                onChange={(e) => setConfidenceGate(parseFloat(e.target.value))}
                className="w-full accent-emerald-500 cursor-pointer"
              />
            </div>

            {/* Dusk Enhancer Toggle */}
            <div className="flex items-center justify-between pt-1 border-t border-slate-800">
              <div className="flex items-center space-x-2">
                <Moon className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-xs font-mono text-slate-300 block">Dusk Low-Light</span>
                  <span className="text-[10px] text-slate-400 block">Koreksi gamma rekaman senja</span>
                </div>
              </div>
              <input
                type="checkbox"
                checked={duskEnhancer}
                onChange={(e) => setDuskEnhancer(e.target.checked)}
                className="w-4 h-4 accent-emerald-500 cursor-pointer"
              />
            </div>

            {/* Execute Button */}
            <button
              type="button"
              disabled={loading}
              onClick={activeMediaTab === 'image' ? handleRunImageAnalysis : handleRunVideoAnalysis}
              className="w-full flex items-center justify-center space-x-2 py-2.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-semibold text-xs tracking-wider transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>
                {loading
                  ? (activeMediaTab === 'image' ? 'MEMPROSES CITRA...' : 'MEMINDAI VIDEO (GPU)...')
                  : (activeMediaTab === 'image' ? 'JALANKAN ANALISIS FOTO' : 'JALANKAN ANALISIS VIDEO')}
              </span>
            </button>
          </div>
        </div>

        {/* Kolom Kanan: Results & Visualisation */}
        <div className="lg:col-span-2 space-y-4">
          {activeMediaTab === 'image' ? (
            /* ================= HASIL ANALISIS FOTO ================= */
            <div className="space-y-4">
              <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                    Pratinjau Citra Teranotasi
                  </h2>
                  {imageResult && (
                    <span className="text-[11px] font-mono text-slate-400">
                      {imageResult.resolution.width}x{imageResult.resolution.height} px // {imageResult.latency_ms} ms
                    </span>
                  )}
                </div>

                <div className="relative bg-slate-950 rounded border border-slate-800 min-h-[320px] flex items-center justify-center overflow-hidden">
                  {imageResult?.annotated_image_url ? (
                    <img
                      src={imageResult.annotated_image_url}
                      alt="Hasil Anotasi Taktis"
                      className="max-h-[500px] w-auto object-contain mx-auto"
                    />
                  ) : imagePreviewUrl ? (
                    <img
                      src={imagePreviewUrl}
                      alt="Pratinjau Foto Upload"
                      className="max-h-[500px] w-auto object-contain mx-auto opacity-70"
                    />
                  ) : (
                    <div className="text-center p-8 space-y-2">
                      <ImageIcon className="w-10 h-10 text-slate-600 mx-auto" />
                      <p className="text-xs font-mono text-slate-500">
                        Pilih sampel foto atau unggah berkas citra, lalu klik Jalankan Analisis Foto.
                      </p>
                    </div>
                  )}
                </div>

                {imageResult && (
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-center font-mono">
                    <div className="bg-slate-950 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Total Target</span>
                      <span className="text-base font-bold text-white">
                        {imageResult.threat_summary.total_objects}
                      </span>
                    </div>
                    <div className="bg-slate-950 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Target Bahaya</span>
                      <span className="text-base font-bold text-red-400">
                        {imageResult.threat_summary.hazard_count}
                      </span>
                    </div>
                    <div className="bg-slate-950 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Target Netral</span>
                      <span className="text-base font-bold text-emerald-400">
                        {imageResult.threat_summary.neutral_count}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Rincian Tabel Deteksi Foto */}
              {imageResult && (
                <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <FileText className="w-3.5 h-3.5 text-slate-400" />
                      <span>Rincian Log Deteksi Citra ({imageResult.detections.length})</span>
                    </h3>
                    <button
                      type="button"
                      onClick={downloadImageCSV}
                      className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Ekspor CSV</span>
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 bg-slate-950">
                          <th className="py-2 px-2.5">#</th>
                          <th className="py-2 px-2.5">Target</th>
                          <th className="py-2 px-2.5">Confidence</th>
                          <th className="py-2 px-2.5">Status</th>
                          <th className="py-2 px-2.5">Estimasi Jarak</th>
                          <th className="py-2 px-2.5">Keterangan</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {imageResult.detections.map((det: any) => (
                          <tr key={det.id} className="hover:bg-slate-850">
                            <td className="py-2 px-2.5 text-slate-500">{det.id}</td>
                            <td className="py-2 px-2.5 text-white font-medium">{det.display_name}</td>
                            <td className="py-2 px-2.5 text-slate-300">{Math.round(det.confidence * 100)}%</td>
                            <td className="py-2 px-2.5">
                              <span
                                className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  det.threat === 'HAZARD'
                                    ? 'bg-red-950 text-red-400 border border-red-800'
                                    : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                }`}
                              >
                                {det.threat}
                              </span>
                            </td>
                            <td className="py-2 px-2.5 text-slate-400">
                              {det.estimated_distance_m ? `${det.estimated_distance_m} m` : 'N/A'}
                            </td>
                            <td className="py-2 px-2.5 text-slate-400">{det.threat_label}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* ================= HASIL ANALISIS VIDEO ================= */
            <div className="space-y-4">
              <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                    Hasil Pemindaian Video Rekaman
                  </h2>
                  {videoResult && (
                    <span className="text-[11px] font-mono text-slate-400">
                      {videoResult.duration_s}s ({videoResult.total_frames} frame) // Diproses dalam {videoResult.latency_ms} ms
                    </span>
                  )}
                </div>

                {videoResult ? (
                  <div className="space-y-4">
                    {/* Ringkasan Statistik Rekaman */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center font-mono">
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-400 block uppercase">Frame Disampling</span>
                        <span className="text-base font-bold text-white">
                          {videoResult.sampled_frames} / {videoResult.total_frames}
                        </span>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-400 block uppercase">Total Deteksi</span>
                        <span className="text-base font-bold text-signal-cyan">
                          {videoResult.threat_summary.total_detections}
                        </span>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-400 block uppercase">Bahaya (Hazard)</span>
                        <span className="text-base font-bold text-red-400">
                          {videoResult.threat_summary.hazard_count}
                        </span>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-400 block uppercase">Netral (Aman)</span>
                        <span className="text-base font-bold text-emerald-400">
                          {videoResult.threat_summary.neutral_count}
                        </span>
                      </div>
                    </div>

                    {/* Breakdown Kelas Objek */}
                    <div className="bg-slate-950 p-3 rounded border border-slate-800">
                      <span className="text-[11px] font-mono text-slate-400 block mb-2 uppercase">
                        Sebaran Kelas Terdeteksi:
                      </span>
                      <div className="flex flex-wrap gap-2 text-xs font-mono">
                        {mode === 'drone' ? (
                          <>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Pohon: <b className="text-white">{videoResult.threat_summary.drone_stats.tree || 0}</b>
                            </span>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Sipil: <b className="text-white">{videoResult.threat_summary.drone_stats.civilian || 0}</b>
                            </span>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Prajurit: <b className="text-white">{videoResult.threat_summary.drone_stats.soldier || 0}</b>
                            </span>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Kendaraan: <b className="text-white">{videoResult.threat_summary.drone_stats.military_vehicle || 0}</b>
                            </span>
                          </>
                        ) : (
                          <>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Biota/Ikan: <b className="text-white">{videoResult.threat_summary.rov_stats.marine_life || 0}</b>
                            </span>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Karang: <b className="text-white">{videoResult.threat_summary.rov_stats.coral_reef || 0}</b>
                            </span>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Penyelam: <b className="text-white">{videoResult.threat_summary.rov_stats.diver || 0}</b>
                            </span>
                            <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Submarine: <b className="text-white">{videoResult.threat_summary.rov_stats.submarine || 0}</b>
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Galeri Keyframe Snapshot */}
                    {videoResult.keyframes?.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-[11px] font-mono text-slate-400 block uppercase">
                          Cuplikan Frame Kunci (Keyframes Snapshot):
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                          {videoResult.keyframes.map((kf: any, i: number) => (
                            <div key={i} className="bg-slate-950 p-2 rounded border border-slate-800 space-y-1.5">
                              <img
                                src={kf.image_url}
                                alt={`Frame ${kf.frame}`}
                                className="w-full h-auto rounded border border-slate-800"
                              />
                              <div className="flex items-center justify-between text-[11px] font-mono">
                                <span className="text-emerald-400 font-bold">Frame #{kf.frame}</span>
                                <span className="text-slate-400">T+{kf.timestamp_s}s</span>
                              </div>
                              <div className="text-[10px] font-mono text-slate-300 truncate">
                                {kf.targets.join(', ')}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center p-12 space-y-2 bg-slate-950 rounded border border-slate-800">
                    <Film className="w-10 h-10 text-slate-600 mx-auto" />
                    <p className="text-xs font-mono text-slate-400">
                      Pilih sampel video atau unggah berkas rekaman patroli MP4, lalu klik Jalankan Analisis Video.
                    </p>
                    <p className="text-[11px] font-mono text-slate-500">
                      Sistem memindai frame secara temporal di GPU dan merangkum seluruh deteksi dalam bentuk keyframe & log CSV.
                    </p>
                  </div>
                )}
              </div>

              {/* Rincian Log Deteksi Video */}
              {videoResult && videoResult.detection_log?.length > 0 && (
                <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <span>Rincian Kronologis Deteksi Video ({videoResult.detection_log.length})</span>
                    </h3>
                    <button
                      type="button"
                      onClick={downloadVideoCSV}
                      className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Ekspor Rekap Video (CSV)</span>
                    </button>
                  </div>

                  <div className="overflow-x-auto max-h-[360px] scrollbar-thin">
                    <table className="w-full text-left text-xs font-mono border-collapse">
                      <thead className="sticky top-0 bg-slate-950 z-10">
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="py-2 px-2.5">Frame</th>
                          <th className="py-2 px-2.5">Waktu</th>
                          <th className="py-2 px-2.5">Target</th>
                          <th className="py-2 px-2.5">Confidence</th>
                          <th className="py-2 px-2.5">Status</th>
                          <th className="py-2 px-2.5">Keterangan</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {videoResult.detection_log.map((log: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-850">
                            <td className="py-1.5 px-2.5 text-slate-500">#{log.frame}</td>
                            <td className="py-1.5 px-2.5 text-slate-400">{log.timestamp_s}s</td>
                            <td className="py-1.5 px-2.5 text-white font-medium">{log.display_name}</td>
                            <td className="py-1.5 px-2.5 text-slate-300">{Math.round(log.confidence * 100)}%</td>
                            <td className="py-1.5 px-2.5">
                              <span
                                className={`inline-block px-1.5 py-0.2 rounded text-[10px] font-bold ${
                                  log.threat === 'HAZARD'
                                    ? 'bg-red-950 text-red-400 border border-red-800'
                                    : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                }`}
                              >
                                {log.threat}
                              </span>
                            </td>
                            <td className="py-1.5 px-2.5 text-slate-400">{log.threat_label}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
