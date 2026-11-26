import React, { useEffect, useRef, useState } from 'react';

interface CompassProps {
  heading: number;
  cardinal: string;
}

export const CompassRibbon: React.FC<CompassProps> = ({ heading, cardinal }) => {
  const width = 340;
  const centerX = width / 2;
  const pxPerDeg = 2.4;

  const ticks: Array<{ deg: number; relDeg: number; x: number; label?: string; isCardinal?: boolean; isNorth?: boolean }> = [];

  for (let d = 0; d < 360; d += 15) {
    const relDeg = ((d - heading + 540) % 360) - 180;
    if (relDeg >= -70 && relDeg <= 70) {
      const x = centerX + relDeg * pxPerDeg;
      let label: string | undefined;
      let isCardinal = false;
      let isNorth = false;

      if (d === 0) {
        label = 'N';
        isCardinal = true;
        isNorth = true;
      } else if (d === 90) {
        label = 'E';
        isCardinal = true;
      } else if (d === 180) {
        label = 'S';
        isCardinal = true;
      } else if (d === 270) {
        label = 'W';
        isCardinal = true;
      } else if (d === 45) {
        label = 'NE';
        isCardinal = true;
      } else if (d === 135) {
        label = 'SE';
        isCardinal = true;
      } else if (d === 225) {
        label = 'SW';
        isCardinal = true;
      } else if (d === 315) {
        label = 'NW';
        isCardinal = true;
      } else if (d % 30 === 0) {
        label = d.toString().padStart(3, '0');
      }

      ticks.push({ deg: d, relDeg, x, label, isCardinal, isNorth });
    }
  }

  return (
    <div className="relative w-[280px] sm:w-[340px] h-[36px] bg-slate-950/85 backdrop-blur-md border border-slate-700/60 rounded px-2 overflow-hidden pointer-events-none select-none flex flex-col justify-end">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 flex flex-col items-center z-10">
        <div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[5px] border-t-signal-cyan" />
        <div className="w-px h-2 bg-signal-cyan/90" />
      </div>

      <svg className="w-full h-[22px] overflow-hidden" viewBox={`0 0 ${width} 22`}>
        {ticks.map((t, idx) => (
          <g key={idx}>
            <line
              x1={t.x}
              y1={22}
              x2={t.x}
              y2={t.isNorth ? 8 : t.isCardinal ? 10 : t.label ? 12 : 16}
              stroke={t.isNorth ? '#FF3B30' : t.isCardinal ? '#00FF66' : '#64748B'}
              strokeWidth={t.isNorth ? 2 : t.isCardinal ? 1.5 : 1}
            />
            {t.label && (
              <text
                x={t.x}
                y={t.isCardinal ? 8 : 9}
                textAnchor="middle"
                fontSize={t.isNorth ? '10' : t.isCardinal ? '9' : '8'}
                fontWeight={t.isCardinal ? '700' : '500'}
                fontFamily="JetBrains Mono, monospace"
                fill={t.isNorth ? '#FF3B30' : t.isCardinal ? '#00FF66' : '#94A3B8'}
              >
                {t.label}
              </text>
            )}
          </g>
        ))}
      </svg>

      <div className="absolute bottom-0.5 left-1/2 -translate-x-1/2 text-[10px] font-mono font-bold text-white bg-slate-900/90 border border-slate-700/80 px-1.5 py-0.2 rounded leading-tight tracking-wider">
        {Math.round(heading).toString().padStart(3, '0')}° {cardinal}
      </div>
    </div>
  );
};

export const CircularCompassDial: React.FC<CompassProps> = ({ heading, cardinal }) => {
  const size = 110;
  const center = size / 2;
  const radius = 48;
  const innerRadius = 40;
  const ticks = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330];

  const prevHeadingRef = useRef<number>(heading);
  const [unwrappedRotation, setUnwrappedRotation] = useState<number>(-heading);

  useEffect(() => {
    // Hitung delta terpendek [-180, +180] agar animasi lintas 0/360 tidak berputar penuh
    const rawDiff = heading - prevHeadingRef.current;
    const shortestDelta = ((rawDiff + 540) % 360) - 180;
    prevHeadingRef.current = heading;
    if (shortestDelta !== 0) {
      setUnwrappedRotation((prev) => prev - shortestDelta);
    }
  }, [heading]);

  return (
    <div className="relative w-[110px] h-[110px] bg-slate-950/85 backdrop-blur-md border border-slate-700/60 rounded-full shadow-2xl flex items-center justify-center pointer-events-none select-none">
      <div className="absolute top-1 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center">
        <div className="w-0 h-0 border-l-[3.5px] border-l-transparent border-r-[3.5px] border-r-transparent border-t-[5px] border-t-signal-cyan" />
      </div>

      <svg
        className="w-full h-full"
        viewBox={`0 0 ${size} ${size}`}
        style={{
          transform: `rotate(${unwrappedRotation}deg)`,
          transition: 'transform 0.15s ease-out',
        }}
      >
        <circle cx={center} cy={center} r={radius} fill="none" stroke="#334155" strokeWidth="1" />
        <circle
          cx={center}
          cy={center}
          r={innerRadius - 8}
          fill="none"
          stroke="#1E293B"
          strokeWidth="0.8"
          strokeDasharray="2 3"
        />

        {ticks.map((deg) => {
          const rad = (deg - 90) * (Math.PI / 180);
          const isCardinal = deg % 90 === 0;
          const isNorth = deg === 0;
          const tickLen = isNorth ? 8 : isCardinal ? 6 : 4;

          const x1 = center + radius * Math.cos(rad);
          const y1 = center + radius * Math.sin(rad);
          const x2 = center + (radius - tickLen) * Math.cos(rad);
          const y2 = center + (radius - tickLen) * Math.sin(rad);

          const textR = radius - 15;
          const tx = center + textR * Math.cos(rad);
          const ty = center + textR * Math.sin(rad) + 3;

          let label = '';
          if (deg === 0) label = 'N';
          else if (deg === 90) label = 'E';
          else if (deg === 180) label = 'S';
          else if (deg === 270) label = 'W';

          return (
            <g key={deg}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={isNorth ? '#FF3B30' : isCardinal ? '#00FF66' : '#64748B'}
                strokeWidth={isNorth ? 2 : isCardinal ? 1.5 : 1}
              />
              {label && (
                <text
                  x={tx}
                  y={ty}
                  textAnchor="middle"
                  fontSize={isNorth ? '9' : '8'}
                  fontWeight={isNorth ? '800' : '700'}
                  fontFamily="JetBrains Mono, monospace"
                  fill={isNorth ? '#FF3B30' : isCardinal ? '#00FF66' : '#94A3B8'}
                  transform={`rotate(${deg}, ${tx}, ${ty - 3})`}
                >
                  {label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none">
        <div className="w-1.5 h-1.5 rounded-full bg-signal-cyan/80 mb-0.5" />
        <span className="text-[11px] font-mono font-bold text-white leading-none font-telemetry">
          {Math.round(heading).toString().padStart(3, '0')}°
        </span>
        <span className="text-[9px] font-mono text-signal-cyan font-bold tracking-wider">
          {cardinal}
        </span>
      </div>
    </div>
  );
};
