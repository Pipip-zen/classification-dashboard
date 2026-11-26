import React, { useEffect, useRef } from 'react';
import type { ChannelId } from '../../types';
import { buildWsUrl } from '../../utils/session';

interface RemoteStreamCanvasProps {
  channelId: ChannelId;
  mode: 'main' | 'pip';
  className?: string;
}

/**
 * Menampilkan stream JPEG biner via WebSocket (/ws/view/{channel}) di canvas HTML5.
 * Menggambar frame baru menimpa canvas sebelumnya agar transisi channel tidak berkedip.
 */
export const RemoteStreamCanvas: React.FC<RemoteStreamCanvasProps> = ({
  channelId,
  mode,
  className = 'w-full h-full object-contain pointer-events-none select-none',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    let active = true;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let decoding = false;

    const connect = () => {
      if (!active) return;
      const url = buildWsUrl(`/ws/view/${channelId}?mode=${mode}`);
      ws = new WebSocket(url);
      ws.binaryType = 'blob';

      ws.onmessage = async (event) => {
        if (!active || !(event.data instanceof Blob) || decoding) return;
        const canvas = canvasRef.current;
        if (!canvas) return;
        decoding = true;
        try {
          const bitmap = await createImageBitmap(event.data);
          if (!active) {
            bitmap.close();
            return;
          }
          if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
          }
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(bitmap, 0, 0);
          }
          bitmap.close();
        } catch {
          // Lewati frame rusak tanpa memutus stream
        } finally {
          decoding = false;
        }
      };

      ws.onclose = () => {
        if (active) {
          reconnectTimer = setTimeout(connect, 1500);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      active = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws && ws.readyState < WebSocket.CLOSING) {
        ws.close();
      }
    };
  }, [channelId, mode]);

  return (
    <canvas
      ref={canvasRef}
      width={mode === 'pip' ? 420 : 1280}
      height={mode === 'pip' ? 236 : 720}
      className={className}
    />
  );
};
