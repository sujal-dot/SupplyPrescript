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
    sm: 'px-3 py-1.5 text-xs rounded-xl gap-1.5',
    md: 'px-4 py-2 text-sm rounded-xl gap-2',
    lg: 'px-6 py-3 text-base rounded-2xl gap-2.5',
  };

  const variantStyles = {
    primary: 'glass-button-primary text-white font-medium',
    secondary: 'glass-button-secondary text-slate-200 hover:text-white font-medium',
    outline: 'bg-transparent border border-white/15 text-slate-300 hover:text-white hover:bg-white/[0.06] hover:border-cyan-400/30',
    ghost: 'bg-transparent text-slate-400 hover:text-slate-100 hover:bg-white/[0.05]',
    danger: 'bg-rose-500/15 border border-rose-400/30 text-rose-300 hover:bg-rose-500/25 hover:border-rose-400/50 shadow-sm shadow-rose-500/20',
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
        <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
      ) : Icon ? (
        <Icon className="h-4 w-4 shrink-0" />
      ) : null}
      <span>{children}</span>
    </button>
  );
}
