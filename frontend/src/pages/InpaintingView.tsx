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

  useEffect(() => {
    if (!selectedFile) return;
    const img = new Image();
    const url = URL.createObjectURL(selectedFile);
    img.src = url;
    img.onload = () => {
      const canvas = canvasRef.current;
      const maskCanvas = maskCanvasRef.current;
      if (!canvas || !maskCanvas) return;

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

    maskCtx.fillStyle = 'white';
    maskCtx.beginPath();
    maskCtx.arc(x, y, brushSize, 0, Math.PI * 2);
    maskCtx.fill();

    ctx.fillStyle = 'rgba(239, 68, 68, 0.45)';
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
          alert(data.detail || "Gagal memproses inpainting.");
        }
      } catch (e) {
        alert("Gagal menghubungi server backend.");
      } finally {
        setLoading(false);
      }
    }, 'image/png');
  };

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-5">
      <div className="border-b border-slate-800 pb-3">
        <h1 className="text-lg font-bold font-mono text-slate-100 flex items-center space-x-2">
          <Scissors className="w-5 h-5 text-signal-cyan" />
          <span>TACTICAL INPAINTING</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Tandai wilayah objek dengan kuas mouse untuk proses rekonstruksi citra menggunakan algoritma Telea atau Navier-Stokes.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="space-y-4">
          <div className="bg-slate-900 p-4 rounded border border-slate-800 space-y-3">
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              Unggah Citra Target
            </h2>

            <label className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded p-5 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950">
              <Upload className="w-6 h-6 text-slate-400 mb-2" />
              <span className="text-xs font-mono text-slate-300 text-center">
                {selectedFile ? selectedFile.name : 'Pilih foto target'}
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

            <div>
              <div className="flex justify-between items-center mb-1 text-xs font-mono">
                <span className="text-slate-400 flex items-center space-x-1">
                  <Paintbrush className="w-3.5 h-3.5" />
                  <span>Ukuran Kuas:</span>
                </span>
                <span className="font-bold text-signal-cyan font-telemetry">{brushSize} px</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                value={brushSize}
                onChange={(e) => setBrushSize(parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-950 rounded appearance-none cursor-pointer accent-signal-cyan"
              />
            </div>

            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">Algoritma:</label>
              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-white font-mono focus:border-slate-500 focus:outline-none"
              >
                <option value="telea">Fast Marching (Telea)</option>
                <option value="ns">Navier-Stokes (Preservasi Fluida)</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1 text-xs font-mono">
                <span className="text-slate-400">Radius Inpaint:</span>
                <span className="font-bold text-signal-cyan font-telemetry">{radius} px</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                value={radius}
                onChange={(e) => setRadius(parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-950 rounded appearance-none cursor-pointer accent-signal-cyan"
              />
            </div>

            <div className="space-y-2 pt-1">
              <button
                type="button"
                onClick={handleRunInpaint}
                disabled={loading || !imageLoaded}
                className="w-full py-2.5 rounded bg-signal-cyan hover:bg-cyan-500 text-slate-950 font-mono font-bold text-xs tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading ? 'MEMPROSES INPAINTING...' : 'TERAPKAN INPAINTING'}
              </button>

              <button
                type="button"
                onClick={handleResetMask}
                disabled={!imageLoaded}
                className="w-full py-2 rounded bg-slate-850 hover:bg-slate-800 text-slate-300 font-mono text-xs border border-slate-700 transition-colors flex items-center justify-center space-x-1.5"
              >
                <Eraser className="w-3.5 h-3.5" />
                <span>Bersihkan Coretan Mask</span>
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900 p-4 rounded border border-slate-800">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
              <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                {resultUrl ? 'HASIL INPAINTING' : 'KANVAS MENGGAMBAR MASK'}
              </h2>
              {resultUrl && (
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => setResultUrl(null)}
                    className="px-2.5 py-1 rounded bg-slate-850 hover:bg-slate-800 text-slate-300 font-mono text-xs border border-slate-700"
                  >
                    Edit Ulang
                  </button>
                  <a
                    href={resultUrl}
                    download="tactical_inpaint_result.jpg"
                    className="flex items-center space-x-1 px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-signal-cyan font-mono text-xs border border-slate-700"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Unduh Hasil</span>
                  </a>
                </div>
              )}
            </div>

            <div className="w-full h-[440px] bg-slate-950 rounded border border-slate-800 flex items-center justify-center overflow-auto p-2 relative">
              {resultUrl ? (
                <img
                  src={resultUrl}
                  alt="Hasil Inpainting"
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
                    className={`max-h-[420px] max-w-full object-contain cursor-crosshair border border-slate-800 ${
                      !imageLoaded ? 'hidden' : 'block'
                    }`}
                  />
                  <canvas ref={maskCanvasRef} className="hidden" />
                  
                  {!imageLoaded && (
                    <div className="text-center text-slate-500 font-mono text-xs py-20">
                      Pilih gambar untuk mulai menandai wilayah mask.
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
