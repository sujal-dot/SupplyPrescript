import React from 'react';
import { AlertCircle, RefreshCw, Layers, ShieldCheck } from 'lucide-react';
import GlassButton from '../ui/GlassButton';

export function DashboardLoadingState({ message = 'Loading optimization telemetry...' }) {
  return (
    <div className="glass-card p-12 rounded-2xl border border-white/[0.08] flex flex-col items-center justify-center text-center space-y-4">
      <div className="relative">
        <div className="h-12 w-12 rounded-full border-2 border-cyan-400/20 border-t-cyan-400 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-cyan-400" />
        </div>
      </div>
      <div>
        <h4 className="text-sm font-bold text-white tracking-tight">{message}</h4>
        <p className="text-xs text-slate-400 mt-1">
          Querying PostgreSQL database and mixed-integer prescriptive solver...
        </p>
      </div>
    </div>
  );
}

export function DashboardErrorState({
  title = 'Failed to load optimization data',
  message = 'An unexpected error occurred while processing supply-chain telemetry.',
  onRetry,
}) {
  return (
    <div className="glass-card p-8 rounded-2xl border border-rose-500/30 bg-rose-500/5 text-center flex flex-col items-center justify-center space-y-3">
      <div className="p-3 rounded-2xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <AlertCircle className="h-6 w-6" />
      </div>
      <div>
        <h4 className="text-sm font-bold text-white tracking-tight">{title}</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-md">{message}</p>
      </div>
      {onRetry && (
        <GlassButton variant="secondary" size="sm" icon={RefreshCw} onClick={onRetry}>
          Retry Evaluation
        </GlassButton>
      )}
    </div>
  );
}

export function DashboardEmptyState({
  title = 'No Optimization Target Selected',
  message = 'Select an active shipment from the risk monitor below to evaluate candidate decisions.',
  onAction,
  actionLabel = 'Select First Shipment',
}) {
  return (
    <div className="glass-card p-10 rounded-2xl border border-white/[0.08] text-center flex flex-col items-center justify-center space-y-3">
      <div className="p-3 rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
        <Layers className="h-6 w-6" />
      </div>
      <div>
        <h4 className="text-sm font-bold text-white tracking-tight">{title}</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-md">{message}</p>
      </div>
      {onAction && (
        <GlassButton variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </GlassButton>
      )}
    </div>
  );
}
