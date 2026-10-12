import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import GlassButton from './GlassButton';

export default function EmptyState({
  title = 'No Data Available',
  description = 'No records match the selected filter criteria or the backend service is currently offline.',
  icon: Icon = AlertCircle,
  actionLabel,
  onAction,
  className = '',
}) {
  return (
    <div className={`glass-card p-10 rounded-2xl text-center flex flex-col items-center justify-center max-w-lg mx-auto my-8 ${className}`}>
      <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-400/20 flex items-center justify-center text-cyan-400 mb-4 shadow-lg shadow-cyan-500/15">
        <Icon className="h-7 w-7" />
      </div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400 max-w-md leading-relaxed mb-6">
        {description}
      </p>
      {actionLabel && onAction && (
        <GlassButton variant="primary" size="md" icon={RefreshCw} onClick={onAction}>
          {actionLabel}
        </GlassButton>
      )}
    </div>
  );
}
