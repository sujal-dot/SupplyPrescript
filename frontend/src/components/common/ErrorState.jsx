import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import GlassButton from '../ui/GlassButton';

export default function ErrorState({
  title = 'Operational Error Encountered',
  message = 'An unexpected error occurred while communicating with the optimization engine.',
  onRetry = null,
  className = '',
}) {
  return (
    <div
      className={`glass-card p-6 rounded-2xl border border-rose-500/30 bg-rose-500/5 ${className}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start space-x-3">
          <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20 shrink-0">
            <AlertTriangle className="h-5 w-5 text-rose-400" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-rose-200 tracking-tight">{title}</h4>
            <p className="text-xs text-rose-300/80 mt-1 leading-relaxed">{message}</p>
          </div>
        </div>
        {onRetry && (
          <GlassButton
            variant="secondary"
            size="sm"
            icon={RefreshCw}
            onClick={onRetry}
            className="shrink-0"
          >
            Retry
          </GlassButton>
        )}
      </div>
    </div>
  );
}
