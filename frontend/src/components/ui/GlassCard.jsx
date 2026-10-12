import React from 'react';

export default function GlassCard({
  children,
  className = '',
  interactive = false,
  glow = null, // 'cyan', 'blue', 'emerald', 'rose', 'amber'
  onClick,
  ...props
}) {
  const glowStyles = {
    cyan: 'hover:border-cyan-400/40 hover:shadow-[0_16px_40px_rgba(0,0,0,0.35),0_0_24px_rgba(34,211,238,0.15)]',
    blue: 'hover:border-blue-400/40 hover:shadow-[0_16px_40px_rgba(0,0,0,0.35),0_0_24px_rgba(59,130,246,0.15)]',
    emerald: 'hover:border-emerald-400/40 hover:shadow-[0_16px_40px_rgba(0,0,0,0.35),0_0_24px_rgba(52,211,153,0.15)]',
    rose: 'hover:border-rose-400/40 hover:shadow-[0_16px_40px_rgba(0,0,0,0.35),0_0_24px_rgba(251,113,133,0.15)]',
    amber: 'hover:border-amber-400/40 hover:shadow-[0_16px_40px_rgba(0,0,0,0.35),0_0_24px_rgba(251,191,36,0.15)]',
  };

  const baseClass = interactive ? 'glass-card-interactive' : 'glass-card';
  const glowClass = interactive && glow ? glowStyles[glow] || '' : '';

  return (
    <div
      className={`${baseClass} p-6 relative overflow-hidden ${glowClass} ${className}`}
      onClick={onClick}
      {...props}
    >
      {children}
    </div>
  );
}
