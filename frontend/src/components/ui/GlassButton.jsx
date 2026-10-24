import React from 'react';
import { Loader2 } from 'lucide-react';

export default function GlassButton({
  children,
  variant = 'primary', // 'primary', 'secondary', 'outline', 'ghost', 'danger'
  size = 'md', // 'sm', 'md', 'lg'
  loading = false,
  disabled = false,
  icon: Icon,
  className = '',
  onClick,
  type = 'button',
  ...props
}) {
  const sizeStyles = {
    sm: 'px-3.5 py-1.5 text-xs rounded-full gap-1.5',
    md: 'px-4.5 py-2 text-sm rounded-full gap-2',
    lg: 'px-6 py-2.5 text-base rounded-full gap-2.5',
  };

  const variantStyles = {
    primary: 'glass-button-primary text-white font-medium shadow-[0_4px_16px_rgba(239,68,68,0.35),inset_0_1px_1px_rgba(255,255,255,0.40)]',
    secondary: 'glass-button-secondary text-slate-200 hover:text-white font-medium shadow-[inset_0_1px_1px_rgba(255,255,255,0.20)]',
    outline: 'bg-white/[0.03] backdrop-blur-md border border-white/20 text-slate-200 hover:text-white hover:bg-white/[0.08] hover:border-red-400/50 shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)]',
    ghost: 'bg-transparent text-slate-300 hover:text-white hover:bg-white/[0.08] backdrop-blur-sm',
    danger: 'bg-gradient-to-r from-rose-600/30 to-red-600/20 backdrop-blur-md border border-rose-400/40 text-rose-200 hover:bg-rose-600/40 hover:border-rose-400/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.25),0_4px_16px_rgba(244,63,94,0.30)]',
  };

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`inline-flex items-center justify-center transition-all duration-200 cursor-pointer select-none disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin text-red-400" />
      ) : Icon ? (
        <Icon className="h-4 w-4 shrink-0" />
      ) : null}
      <span>{children}</span>
    </button>
  );
}
