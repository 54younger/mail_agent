import { useState } from 'react';
import type { TrendPoint } from '../../../api/jobs';
import { niceMax, smoothPath } from './scale';

// Applications-over-time area chart. Hand-rolled SVG: gradient fill, gridlines,
// and a hover crosshair with a value bubble.
const W = 640;
const H = 220;
const PAD = { top: 18, right: 18, bottom: 30, left: 34 };
const GRID = 4;

interface Props {
  data: TrendPoint[];
}

export function TrendChart({ data }: Props) {
  const [hover, setHover] = useState<number | null>(null);

  if (data.length === 0) {
    return (
      <div className="flex h-[220px] items-center justify-center text-sm text-slate-400">
        暂无投递数据
      </div>
    );
  }

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const maxY = niceMax(Math.max(...data.map((d) => d.count)));
  const xAt = (i: number) => PAD.left + (data.length > 1 ? (i / (data.length - 1)) * innerW : innerW / 2);
  const yAt = (v: number) => PAD.top + innerH - (v / maxY) * innerH;

  const pts = data.map((d, i) => [xAt(i), yAt(d.count)] as [number, number]);
  const line = smoothPath(pts);
  const baseY = PAD.top + innerH;
  const area = `${line} L ${pts[pts.length - 1][0]} ${baseY} L ${pts[0][0]} ${baseY} Z`;

  const active = hover != null ? data[hover] : null;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      role="img"
      aria-label="投递数量随日期分布"
      onMouseLeave={() => setHover(null)}
    >
      <defs>
        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* horizontal gridlines + y labels */}
      {Array.from({ length: GRID + 1 }, (_, i) => {
        const v = (maxY / GRID) * i;
        const gy = yAt(v);
        return (
          <g key={i}>
            <line x1={PAD.left} y1={gy} x2={W - PAD.right} y2={gy} stroke="#eef2f7" strokeWidth={1} />
            <text x={PAD.left - 6} y={gy + 3} textAnchor="end" className="fill-slate-400 text-[9px]">
              {Math.round(v)}
            </text>
          </g>
        );
      })}

      <path d={area} fill="url(#trendFill)" />
      <path d={line} fill="none" stroke="#8b5cf6" strokeWidth={2.5} strokeLinecap="round" />

      {/* hover crosshair + point */}
      {active && hover != null && (
        <g>
          <line
            x1={xAt(hover)}
            y1={PAD.top}
            x2={xAt(hover)}
            y2={baseY}
            stroke="#c4b5fd"
            strokeWidth={1}
            strokeDasharray="3 3"
          />
          <circle cx={xAt(hover)} cy={yAt(active.count)} r={4} fill="#8b5cf6" stroke="#fff" strokeWidth={2} />
        </g>
      )}

      {/* x labels: first, middle, last to avoid crowding */}
      {[0, Math.floor((data.length - 1) / 2), data.length - 1]
        .filter((v, i, a) => a.indexOf(v) === i)
        .map((i) => (
          <text key={i} x={xAt(i)} y={H - 8} textAnchor="middle" className="fill-slate-400 text-[9px]">
            {data[i].date.slice(5)}
          </text>
        ))}

      {/* invisible hit targets for hover */}
      {data.map((_, i) => (
        <rect
          key={i}
          x={xAt(i) - innerW / data.length / 2}
          y={PAD.top}
          width={innerW / data.length}
          height={innerH}
          fill="transparent"
          onMouseEnter={() => setHover(i)}
        />
      ))}

      {active && hover != null && (
        <g transform={`translate(${xAt(hover)}, ${yAt(active.count) - 12})`}>
          <rect x={-24} y={-18} width={48} height={16} rx={4} fill="#0f172a" />
          <text x={0} y={-6} textAnchor="middle" className="fill-white text-[9px]">
            {active.date.slice(5)} · {active.count}
          </text>
        </g>
      )}
    </svg>
  );
}
