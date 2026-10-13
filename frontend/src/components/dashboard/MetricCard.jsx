import React from 'react';

export default function MetricCard({
  title,
  value,
  subtitle,
  unit = '',
  icon: Icon,
  variant = 'cyan', // 'cyan', 'blue', 'amber', 'emerald', 'rose'
  badge,
  trend, // { value: '+2.4%', isPositive: true, label: 'vs last month' }
  loading = false,
  empty = false,
  emptyText = 'No data available',
}) {
  const variantStyles = {
    cyan: {
      border: 'hover:border-cyan-400/40',
      iconBg: 'bg-cyan-500/15 border-cyan-400/30 text-cyan-300',
      glow: 'group-hover:shadow-[0_0_25px_rgba(34,211,238,0.15)]',
      textAccent: 'text-cyan-400',
    },
    blue: {
      border: 'hover:border-blue-400/40',
      iconBg: 'bg-blue-500/15 border-blue-400/30 text-blue-300',
      glow: 'group-hover:shadow-[0_0_25px_rgba(59,130,246,0.15)]',
      textAccent: 'text-blue-400',
    },
    emerald: {
      border: 'hover:border-emerald-400/40',
      iconBg: 'bg-emerald-500/15 border-emerald-400/30 text-emerald-300',
      glow: 'group-hover:shadow-[0_0_25px_rgba(52,211,153,0.15)]',
      textAccent: 'text-emerald-400',
    },
    amber: {
      border: 'hover:border-amber-400/40',
      iconBg: 'bg-amber-500/15 border-amber-400/30 text-amber-300',
      glow: 'group-hover:shadow-[0_0_25px_rgba(251,191,36,0.15)]',
      textAccent: 'text-amber-400',
    },
    rose: {
      border: 'hover:border-rose-400/40',
      iconBg: 'bg-rose-500/15 border-rose-400/30 text-rose-300',
      glow: 'group-hover:shadow-[0_0_25px_rgba(251,113,133,0.15)]',
      textAccent: 'text-rose-400',
    },
  };

  const style = variantStyles[variant] || variantStyles.cyan;

  if (loading) {
    return (
      <div className="glass-card p-5 rounded-2xl animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-4 w-28 bg-white/10 rounded-md" />
          <div className="h-9 w-9 bg-white/10 rounded-xl" />
        </div>
        <div className="h-8 w-20 bg-white/10 rounded-lg mb-2" />
        <div className="h-3 w-32 bg-white/5 rounded-md" />
      </div>
    );
  }

  return (
    <div
      className={`glass-card p-5 rounded-2xl relative overflow-hidden group transition-all duration-300 border border-white/[0.08] ${style.border} ${style.glow}`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && (
          <div
            className={`h-9 w-9 rounded-xl flex items-center justify-center border transition-transform duration-300 group-hover:scale-105 ${style.iconBg}`}
          >
            <Icon className="h-4.5 w-4.5" />
          </div>
        )}
      </div>

      <div className="flex items-baseline space-x-2">
        {empty ? (
          <span className="text-xl font-semibold text-slate-500 italic">
            {emptyText}
          </span>
        ) : (
          <>
            <span className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-mono">
              {value !== undefined && value !== null ? value : '—'}
            </span>
            {unit && <span className="text-xs text-slate-400 font-medium">{unit}</span>}
          </>
        )}
      </div>

      {(subtitle || badge || trend) && (
        <div className="mt-2.5 flex items-center justify-between text-xs">
          {subtitle && <span className="text-slate-400 truncate">{subtitle}</span>}
          {badge && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-300 border border-white/[0.08]">
              {badge}
            </span>
          )}
          {trend && (
            <span
              className={`font-mono text-[11px] font-medium flex items-center space-x-1 ${
                trend.isPositive ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              <span>{trend.value}</span>
              {trend.label && (
                <span className="text-slate-500 font-normal ml-1">{trend.label}</span>
              )}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
