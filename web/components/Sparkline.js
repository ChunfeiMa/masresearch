"use client";

// Tiny inline SVG sparkline of recent-run item counts.
export default function Sparkline({ values, color = "#5b8cff", width = 240, height = 44 }) {
  if (!values || values.length === 0) return null;
  const max = Math.max(...values, 1);
  const n = values.length;
  const step = n > 1 ? width / (n - 1) : width;
  const pts = values.map((v, i) => [i * step, height - (v / max) * (height - 6) - 3]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L${width},${height} L0,${height} Z`;
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <path d={area} fill={color} opacity="0.12" />
      <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {pts.length > 0 && (
        <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2.6" fill={color} />
      )}
    </svg>
  );
}
