import React from 'react';

export default function GlassPanel({
  title,
  subtitle,
  icon: Icon,
  actions,
  children,
  className = '',
  contentClassName = '',
}) {
  return (
    <div className={`glass-card p-6 sm:p-7 relative overflow-hidden ${className}`}>
      {(title || subtitle || actions) && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-5 mb-5 border-b border-white/[0.08] gap-3">
          <div className="flex items-center space-x-3">
            {Icon && (
              <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-400/20 text-cyan-400 shrink-0">
                <Icon className="h-5 w-5" />
              </div>
            )}
            <div>
              {title && (
                <h3 className="text-base sm:text-lg font-semibold text-white tracking-wide">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {actions && <div className="flex items-center space-x-2 shrink-0">{actions}</div>}
        </div>
      )}
      <div className={contentClassName}>{children}</div>
    </div>
  );
}
