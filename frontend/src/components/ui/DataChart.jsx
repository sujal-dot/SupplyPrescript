import React, { useState } from 'react';

export default function DataChart({
  title,
  subtitle,
  data = [], // [{ label: 'Mon', value1: 45, value2: 52 }, ...]
  series = [
    { key: 'value1', label: 'Actual Demand', color: '#EF4444' },
    { key: 'value2', label: 'Predicted Demand', color: '#3B82F6', dashed: true },
  ],
  height = 260,
  unit = '',
  className = '',
}) {
  const [hoverIndex, setHoverIndex] = useState(null);

  if (!data || data.length === 0) {
    return (
      <div className={`h-[${height}px] flex items-center justify-center text-slate-500 text-sm`}>
        No telemetry data available for this chart.
      </div>
    );
  }

  // Calculate scales
  const allValues = data.flatMap((d) => series.map((s) => Number(d[s.key]) || 0));
  const minValue = Math.min(0, ...allValues);
  const maxValue = Math.max(10, ...allValues) * 1.15; // 15% headroom

  const paddingLeft = 45;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 35;
  const chartWidth = 700;
  const chartHeight = height;

  const innerWidth = chartWidth - paddingLeft - paddingRight;
  const innerHeight = chartHeight - paddingTop - paddingBottom;

  const getX = (idx) => paddingLeft + (idx / Math.max(1, data.length - 1)) * innerWidth;
  const getY = (val) => paddingTop + innerHeight - ((val - minValue) / (maxValue - minValue)) * innerHeight;

  // Grid lines
  const gridTicks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className={`w-full ${className}`}>
      {/* Header and Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div>
          {title && <h4 className="text-sm font-semibold text-white">{title}</h4>}
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>

        <div className="flex items-center space-x-4 text-xs">
          {series.map((s) => (
            <div key={s.key} className="flex items-center space-x-2">
              <span
                className="w-3 h-0.5 rounded-full inline-block"
                style={{
                  backgroundColor: s.color,
                  borderBottom: s.dashed ? `2px dashed ${s.color}` : 'none',
                }}
              />
              <span className="text-slate-300 font-medium">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG Chart Container */}
      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-auto overflow-visible select-none"
        >
          <defs>
            {series.map((s) => (
              <linearGradient
                key={`grad-${s.key}`}
                id={`grad-${s.key}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={s.color} stopOpacity="0.28" />
                <stop offset="100%" stopColor={s.color} stopOpacity="0.0" />
              </linearGradient>
            ))}
          </defs>

          {/* Grid lines */}
          {gridTicks.map((tick, i) => {
            const yVal = minValue + tick * (maxValue - minValue);
            const yPos = getY(yVal);
            return (
              <g key={i}>
                <line
                  x1={paddingLeft}
                  y1={yPos}
                  x2={chartWidth - paddingRight}
                  y2={yPos}
                  stroke="rgba(255, 255, 255, 0.07)"
                  strokeDasharray="4 4"
                />
                <text
                  x={paddingLeft - 8}
                  y={yPos + 4}
                  fill="#94A3B8"
                  fontSize="10"
                  textAnchor="end"
                  fontFamily="Inter, sans-serif"
                >
                  {Math.round(yVal)}
                  {unit}
                </text>
              </g>
            );
          })}

          {/* Area Fills and Lines */}
          {series.map((s) => {
            const points = data.map((d, i) => `${getX(i)},${getY(Number(d[s.key]) || 0)}`);
            const pathD = `M ${points.join(' L ')}`;
            const firstX = getX(0);
            const lastX = getX(data.length - 1);
            const bottomY = getY(0);
            const areaD = `M ${firstX},${bottomY} L ${points.join(' L ')} L ${lastX},${bottomY} Z`;

            return (
              <g key={s.key}>
                {!s.dashed && (
                  <path
                    d={areaD}
                    fill={`url(#grad-${s.key})`}
                    className="transition-opacity duration-300"
                  />
                )}
                <path
                  d={pathD}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="2.5"
                  strokeDasharray={s.dashed ? '6 5' : 'none'}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {/* Data points */}
                {data.map((d, i) => (
                  <circle
                    key={i}
                    cx={getX(i)}
                    cy={getY(Number(d[s.key]) || 0)}
                    r={hoverIndex === i ? 5 : 3}
                    fill={hoverIndex === i ? '#ffffff' : s.color}
                    stroke="#16070B"
                    strokeWidth="2"
                    className="transition-all duration-150"
                  />
                ))}
              </g>
            );
          })}

          {/* X Axis Labels */}
          {data.map((d, i) => {
            const xPos = getX(i);
            // Show every nth label if too many points
            const step = Math.ceil(data.length / 10);
            if (i % step !== 0 && i !== data.length - 1) return null;

            return (
              <text
                key={i}
                x={xPos}
                y={chartHeight - 10}
                fill="#94A3B8"
                fontSize="10"
                textAnchor="middle"
                fontFamily="Inter, sans-serif"
              >
                {d.label}
              </text>
            );
          })}

          {/* Vertical Hover Guide */}
          {hoverIndex !== null && data[hoverIndex] && (
            <line
              x1={getX(hoverIndex)}
              y1={paddingTop}
              x2={getX(hoverIndex)}
              y2={chartHeight - paddingBottom}
              stroke="rgba(239, 68, 68, 0.45)"
              strokeWidth="1.5"
              strokeDasharray="3 3"
            />
          )}

          {/* Invisible hover overlay rects */}
          {data.map((d, i) => {
            const colWidth = innerWidth / data.length;
            const xPos = getX(i) - colWidth / 2;
            return (
              <rect
                key={i}
                x={xPos}
                y={paddingTop}
                width={colWidth}
                height={innerHeight}
                fill="transparent"
                onMouseEnter={() => setHoverIndex(i)}
                onMouseLeave={() => setHoverIndex(null)}
                className="cursor-crosshair"
              />
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoverIndex !== null && data[hoverIndex] && (
          <div
            className="absolute top-2 pointer-events-none glass-card p-2.5 rounded-xl text-xs shadow-xl z-20 border border-white/20"
            style={{
              left: `${Math.min(
                82,
                Math.max(12, (hoverIndex / (data.length - 1)) * 100)
              )}%`,
              transform: 'translateX(-50%)',
            }}
          >
            <div className="font-semibold text-white mb-1">
              {data[hoverIndex].label}
            </div>
            {series.map((s) => (
              <div key={s.key} className="flex items-center justify-between space-x-3 text-[11px]">
                <span className="text-slate-400">{s.label}:</span>
                <span className="font-mono font-bold" style={{ color: s.color }}>
                  {data[hoverIndex][s.key]}
                  {unit}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
