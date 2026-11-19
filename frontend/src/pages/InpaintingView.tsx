import React, { useState, useRef, useEffect } from 'react';
import { Scissors, Upload, Download, Eraser, Paintbrush } from 'lucide-react';

export const InpaintingView: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [algorithm, setAlgorithm] = useState<string>('telea');
  const [radius, setRadius] = useState<number>(3);
  const [brushSize, setBrushSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [imageLoaded, setImageLoaded] = useState<boolean>(false);

  // Load image ke kanvas saat file berubah
  useEffect(() => {
    if (!selectedFile) return;
    const img = new Image();
    const url = URL.createObjectURL(selectedFile);
    img.src = url;
    img.onload = () => {
      const canvas = canvasRef.current;
      const maskCanvas = maskCanvasRef.current;
      if (!canvas || !maskCanvas) return;

      // Atur ukuran sesuai dimensi asli atau proporsional
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      maskCanvas.width = img.naturalWidth;
      maskCanvas.height = img.naturalHeight;

      const ctx = canvas.getContext('2d');
      const maskCtx = maskCanvas.getContext('2d');
      if (ctx && maskCtx) {
        ctx.drawImage(img, 0, 0);
        maskCtx.fillStyle = 'black';
        maskCtx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
      }
      setImageLoaded(true);
      setResultUrl(null);
    };
  }, [selectedFile]);

  // Gambar Mask di atas Canvas
  const getCanvasCoordinates = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!imageLoaded) return;
    setIsDrawing(true);
    draw(e);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const { x, y } = getCanvasCoordinates(e);
    const canvas = canvasRef.current;
    const maskCanvas = maskCanvasRef.current;
    if (!canvas || !maskCanvas) return;

    const ctx = canvas.getContext('2d');
    const maskCtx = maskCanvas.getContext('2d');
    if (!ctx || !maskCtx) return;

    // Gambar di mask kanvas (Putih = wilayah inpainting)
    maskCtx.fillStyle = 'white';
    maskCtx.beginPath();
    maskCtx.arc(x, y, brushSize, 0, Math.PI * 2);
    maskCtx.fill();

    // Gambar visualisasi merah transparan di kanvas display pengguna
    ctx.fillStyle = 'rgba(255, 59, 48, 0.4)';
    ctx.beginPath();
    ctx.arc(x, y, brushSize, 0, Math.PI * 2);
    ctx.fill();
  };

  const handleResetMask = () => {
    if (!selectedFile) return;
    const img = new Image();
    img.src = URL.createObjectURL(selectedFile);
    img.onload = () => {
      const canvas = canvasRef.current;
      const maskCanvas = maskCanvasRef.current;
      if (!canvas || !maskCanvas) return;
      const ctx = canvas.getContext('2d');
      const maskCtx = maskCanvas.getContext('2d');
      if (ctx && maskCtx) {
        ctx.drawImage(img, 0, 0);
        maskCtx.fillStyle = 'black';
        maskCtx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
      }
      setResultUrl(null);
    };
  };

  const handleRunInpaint = async () => {
    if (!selectedFile || !maskCanvasRef.current) return;
    setLoading(true);

    const maskCanvas = maskCanvasRef.current;
    maskCanvas.toBlob(async (maskBlob) => {
      if (!maskBlob) {
        setLoading(false);
        return;
      }

      const formData = new FormData();
      formData.append('image_file', selectedFile);
      formData.append('mask_file', maskBlob, 'mask.png');
      formData.append('algorithm', algorithm);
      formData.append('radius', radius.toString());

      try {
        const res = await fetch('/api/inpainting/inpaint', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        if (data.success) {
          setResultUrl(data.result_url);
        } else {
          alert(data.detail || "Gagal memproses inpainting");
        }
      } catch (e) {
        alert("Error menghubungi backend");
      } finally {
        setLoading(false);
      }
    }, 'image/png');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-aerospace-border pb-4">
        <div>
          <h1 className="text-xl font-bold font-mono text-white flex items-center space-x-2">
            <Scissors className="w-5 h-5 text-tactical-cyan" />
            <span>TACTICAL INPAINTING: PENGHAPUSAN OBJEK & SENSOR CITRA</span>
          </h1>
          <p className="text-xs text-tactical-muted mt-1">
            Gunakan kuas interaktif untuk menandai wilayah yang ingin dihapus atau disensor (watermark/artefak/kombatan) menggunakan metode Telea atau Navier-Stokes.
          </p>
        </div>
      </div>

      {/* Grid Interaktif */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Kolom Kiri: Kontrol Kuas & Parameter */}
        <div className="space-y-4">
          <div className="tactical-glass p-4 rounded-xl border border-aerospace-border space-y-4">
            <h2 className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider">
              Unggah Citra Target
            </h2>

            {/* Dropzone */}
            <label className="border-2 border-dashed border-aerospace-border hover:border-tactical-cyan/50 rounded-xl p-5 flex flex-col items-center justify-center cursor-pointer transition-all bg-aerospace-panel/40">
              <Upload className="w-7 h-7 text-tactical-cyan mb-2" />
              <span className="text-xs font-mono text-gray-300 text-center">
                {selectedFile ? selectedFile.name : 'Pilih foto untuk inpainting'}
              </span>
              <input 
                type="file" 
                accept="image/*" 
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedFile(e.target.files[0]);
                  }
                }} 
                className="hidden" 
              />
            </label>

            {/* Ukuran Kuas */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-[11px] font-mono text-gray-400 flex items-center space-x-1">
                  <Paintbrush className="w-3.5 h-3.5" />
                  <span>Ukuran Kuas Mask:</span>
                </span>
                <span className="text-xs font-mono font-bold text-tactical-cyan">{brushSize} px</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                value={brushSize}
                onChange={(e) => setBrushSize(parseInt(e.target.value))}
                className="w-full h-1.5 bg-aerospace-panel rounded-lg appearance-none cursor-pointer accent-tactical-cyan"
              />
            </div>

            {/* Algoritma */}
            <div>
              <label className="text-[11px] font-mono text-gray-400 block mb-1">Algoritma Inpainting:</label>
              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value)}
                className="w-full bg-aerospace-bg border border-aerospace-border rounded px-3 py-2 text-xs text-white font-mono focus:border-tactical-cyan focus:outline-none"
              >
                <option value="telea">Fast Marching (Telea) - Cepat & Halus</option>
                <option value="ns">Navier-Stokes (NS) - Preservasi Gradien Fluida</option>
              </select>
            </div>

            {/* Radius Inpaint */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-[11px] font-mono text-gray-400">Radius Sampling:</span>
                <span className="text-xs font-mono font-bold text-tactical-cyan">{radius} px</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                value={radius}
                onChange={(e) => setRadius(parseInt(e.target.value))}
                className="w-full h-1.5 bg-aerospace-panel rounded-lg appearance-none cursor-pointer accent-tactical-cyan"
              />
            </div>

            {/* Tombol Aksi */}
            <div className="space-y-2 pt-2">
              <button
                onClick={handleRunInpaint}
                disabled={loading || !imageLoaded}
                className="w-full py-2.5 rounded-lg bg-tactical-cyan hover:bg-cyan-400 text-black font-mono font-bold text-xs tracking-wider transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-glow-cyan"
              >
                {loading ? 'MEMULIHKAN CITRA...' : 'TERAPKAN INPAINTING'}
              </button>

              <button
                onClick={handleResetMask}
                disabled={!imageLoaded}
                className="w-full py-2 rounded-lg bg-aerospace-panel hover:bg-aerospace-border text-gray-300 font-mono text-xs border border-aerospace-border transition-all flex items-center justify-center space-x-1.5"
              >
                <Eraser className="w-3.5 h-3.5" />
                <span>Bersihkan Coretan Mask</span>
              </button>
            </div>
          </div>
        </div>

        {/* Kolom Kanan: Kanvas Menggambar & Hasil */}
        <div className="lg:col-span-2 space-y-4">
          <div className="tactical-glass p-4 rounded-xl border border-aerospace-border">
            <div className="flex items-center justify-between mb-3 border-b border-aerospace-border pb-2">
              <h2 className="text-xs font-mono font-bold text-gray-300 uppercase tracking-wider">
                {resultUrl ? 'HASIL INPAINTING CITRA BERSIH' : 'KANVAS INTERAKTIF (CORET AREA TARGET DENGAN MOUSE)'}
              </h2>
              {resultUrl && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setResultUrl(null)}
                    className="px-2.5 py-1 rounded bg-aerospace-panel hover:bg-aerospace-border text-gray-300 font-mono text-xs border border-aerospace-border"
                  >
                    Edit Ulang
                  </button>
                  <a
                    href={resultUrl}
                    download="tactical_inpaint_result.jpg"
                    className="flex items-center space-x-1 px-3 py-1 rounded bg-tactical-cyan text-black font-mono font-bold text-xs"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Unduh Hasil</span>
                  </a>
                </div>
              )}
            </div>

            {/* Kanvas Stage */}
            <div className="w-full h-[450px] bg-aerospace-stage rounded-lg border border-aerospace-border flex items-center justify-center overflow-auto p-2 relative">
              {resultUrl ? (
                <img
                  src={resultUrl}
                  alt="Inpainted Clean"
                  className="max-h-full max-w-full object-contain"
                />
              ) : (
                <div className="relative">
                  <canvas
                    ref={canvasRef}
                    onMouseDown={startDrawing}
                    onMouseUp={stopDrawing}
                    onMouseLeave={stopDrawing}
                    onMouseMove={draw}
                    className={`max-h-[420px] max-w-full object-contain cursor-crosshair border border-aerospace-border/40 ${
                      !imageLoaded ? 'hidden' : 'block'
                    }`}
                  />
                  {/* Mask canvas tersembunyi untuk ekspor biner hitam/putih */}
                  <canvas ref={maskCanvasRef} className="hidden" />
                  
                  {!imageLoaded && (
                    <div className="text-center text-gray-500 font-mono text-xs py-20">
                      Pilih gambar untuk mulai menandai objek yang ingin dihapus
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
