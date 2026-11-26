import React, { useEffect, useRef } from 'react';
import type { Detection, ChannelId } from '../../types';

interface LocalOverlayCanvasProps {
  detections: Detection[];
  sourceWidth: number;
  sourceHeight: number;
  channelId: ChannelId;
  showReticle: boolean;
  showLabels: boolean;
}

/**
 * Menggambar kotak deteksi AI dan HUD reticle langsung di atas video lokal Operator (0ms lag).
 */
export const LocalOverlayCanvas: React.FC<LocalOverlayCanvasProps> = ({
  detections,
  sourceWidth,
  sourceHeight,
  channelId,
  showReticle,
  showLabels,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const dpr = window.devicePixelRatio || 1;
    const targetW = Math.round(rect.width * dpr);
    const targetH = Math.round(rect.height * dpr);
    if (canvas.width !== targetW || canvas.height !== targetH) {
      canvas.width = targetW;
      canvas.height = targetH;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const srcW = Math.max(1, sourceWidth);
    const srcH = Math.max(1, sourceHeight);
    const scale = Math.min(rect.width / srcW, rect.height / srcH);
    const drawW = srcW * scale;
    const drawH = srcH * scale;
    const offsetX = (rect.width - drawW) / 2;
    const offsetY = (rect.height - drawH) / 2;

    if (showReticle) {
      const hudColor = channelId === 'rov' ? '#00E5FF' : '#00FF66';
      const cx = rect.width / 2;
      const cy = rect.height / 2;
      ctx.strokeStyle = hudColor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx - 20, cy);
      ctx.lineTo(cx + 20, cy);
      ctx.moveTo(cx, cy - 20);
      ctx.lineTo(cx, cy + 20);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, 10, 0, Math.PI * 2);
      ctx.stroke();
    }

    const isCompact = detections.length > 12;
    for (const det of detections) {
      const [bx1, by1, bx2, by2] = det.bbox;
      const x1 = offsetX + bx1 * scale;
      const y1 = offsetY + by1 * scale;
      const x2 = offsetX + bx2 * scale;
      const y2 = offsetY + by2 * scale;
      const bw = Math.max(4, x2 - x1);
      const bh = Math.max(4, y2 - y1);
      const corner = Math.min(bw, bh) * 0.25;
      const color = det.color_hex || '#00FF66';

      ctx.strokeStyle = color;
      ctx.lineWidth = isCompact ? 1.2 : 2;

      // 4 sudut taktis
      ctx.beginPath();
      ctx.moveTo(x1, y1 + corner); ctx.lineTo(x1, y1); ctx.lineTo(x1 + corner, y1);
      ctx.moveTo(x2 - corner, y1); ctx.lineTo(x2, y1); ctx.lineTo(x2, y1 + corner);
      ctx.moveTo(x1, y2 - corner); ctx.lineTo(x1, y2); ctx.lineTo(x1 + corner, y2);
      ctx.moveTo(x2 - corner, y2); ctx.lineTo(x2, y2); ctx.lineTo(x2, y2 - corner);
      ctx.stroke();

      ctx.lineWidth = 1;
      ctx.strokeRect(x1, y1, bw, bh);

      if (showLabels) {
        const distPart = det.estimated_distance_m != null ? ` ${det.estimated_distance_m}m` : '';
        const text = isCompact
          ? `${det.display_name.split('/')[0].trim()} ${Math.round(det.confidence * 100)}%`
          : `${det.display_name} [${Math.round(det.confidence * 100)}%]${distPart}`;
        ctx.font = '600 11px "JetBrains Mono", monospace';
        const tm = ctx.measureText(text);
        const padX = 4;
        const labelH = 18;
        const ly = Math.max(0, y1 - labelH);

        if (!isCompact) {
          ctx.fillStyle = 'rgba(10, 14, 23, 0.9)';
          ctx.fillRect(x1, ly, tm.width + padX * 2, labelH);
          ctx.strokeStyle = color;
          ctx.strokeRect(x1, ly, tm.width + padX * 2, labelH);
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(text, x1 + padX, ly + 13);
        } else {
          ctx.fillStyle = color;
          ctx.fillText(text, x1 + 2, Math.max(12, y1 - 3));
        }
      }
    }
  }, [detections, sourceWidth, sourceHeight, channelId, showReticle, showLabels]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none select-none z-10"
    />
  );
};
