import React from 'react';

export default function GlassCard({
  children,
  className = '',
  interactive = false,
  glow = null, // 'red', 'rose', 'crimson', 'emerald', 'amber', 'cyan'
  onClick,
  ...props
}) {
  const glowStyles = {
    red: 'hover:border-red-500/50 hover:shadow-[0_20px_48px_-8px_rgba(0,0,0,0.65),0_0_24px_0_rgba(239,68,68,0.25),inset_0_1px_1.5px_0_rgba(255,255,255,0.38)]',
    crimson: 'hover:border-red-600/50 hover:shadow-[0_20px_48px_-8px_rgba(0,0,0,0.65),0_0_24px_0_rgba(220,38,38,0.25),inset_0_1px_1.5px_0_rgba(255,255,255,0.38)]',
    rose: 'hover:border-rose-400/50 hover:shadow-[0_20px_48px_-8px_rgba(0,0,0,0.65),0_0_24px_0_rgba(244,63,94,0.25),inset_0_1px_1.5px_0_rgba(255,255,255,0.38)]',
    cyan: 'hover:border-red-500/50 hover:shadow-[0_20px_48px_-8px_rgba(0,0,0,0.65),0_0_24px_0_rgba(239,68,68,0.25),inset_0_1px_1.5px_0_rgba(255,255,255,0.38)]',
    blue: 'hover:border-rose-400/50 hover:shadow-[0_20px_48px_-8px_rgba(0,0,0,0.65),0_0_24px_0_rgba(244,63,94,0.25),inset_0_1px_1.5px_0_rgba(255,255,255,0.38)]',
    emerald: 'hover:border-emerald-400/50 hover:shadow-[0_20px_48px_-8px_rgba(0,0,0,0.65),0_0_24px_0_rgba(52,211,153,0.20),inset_0_1px_1.5px_0_rgba(255,255,255,0.38)]',
    amber: 'hover:border-amber-400/50 hover:shadow-[0_20px_48px_-8px_rgba(0,0,0,0.65),0_0_24px_0_rgba(251,191,36,0.20),inset_0_1px_1.5px_0_rgba(255,255,255,0.38)]',
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
