import React from 'react';

export default function StatusBadge({
  status,
  variant, // 'success', 'warning', 'error', 'info', 'neutral'
  className = '',
  dot = true,
}) {
  const normalized = (status || '').toLowerCase();

  let autoVariant = variant;
  if (!autoVariant) {
    if (['healthy', 'connected', 'on-time', 'delivered', 'success', 'optimal', 'completed'].includes(normalized)) {
      autoVariant = 'success';
    } else if (['low', 'warning', 'in-transit', 'pending', 'rail', 'reviewing'].includes(normalized)) {
      autoVariant = 'warning';
    } else if (['critical', 'delayed', 'out of stock', 'error', 'unhealthy', 'failed', 'disconnected'].includes(normalized)) {
      autoVariant = 'error';
    } else if (['processing', 'info', 'scheduled', 'road', 'air', 'sea'].includes(normalized)) {
      autoVariant = 'info';
    } else {
      autoVariant = 'neutral';
    }
  }

  const variantStyles = {
    success: 'bg-emerald-500/10 border-emerald-400/25 text-emerald-300 shadow-[inset_0_1px_1px_rgba(52,211,153,0.15)]',
    warning: 'bg-amber-500/10 border-amber-400/25 text-amber-300 shadow-[inset_0_1px_1px_rgba(251,191,36,0.15)]',
    error: 'bg-rose-500/10 border-rose-400/25 text-rose-300 shadow-[inset_0_1px_1px_rgba(251,113,133,0.15)]',
    info: 'bg-cyan-500/10 border-cyan-400/25 text-cyan-300 shadow-[inset_0_1px_1px_rgba(34,211,238,0.15)]',
    neutral: 'bg-slate-700/20 border-slate-600/30 text-slate-300 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]',
  };

  const dotColors = {
    success: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]',
    warning: 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]',
    error: 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)]',
    info: 'bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]',
    neutral: 'bg-slate-400',
  };

  return (
    <span
      className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-md ${variantStyles[autoVariant]} ${className}`}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColors[autoVariant]}`}
        />
      )}
      <span className="capitalize">{status}</span>
    </span>
  );
}
