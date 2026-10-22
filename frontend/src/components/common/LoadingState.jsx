import React from 'react';
import { Sparkles, Loader2 } from 'lucide-react';

export default function LoadingState({
  title = 'Computing Prescriptive Optimization',
  message = 'Retrieving real PostgreSQL logistics records, executing XGBoost inference models, and solving PuLP mixed-integer mathematical programming constraints...',
  className = '',
}) {
  return (
    <div
      className={`glass-card p-8 rounded-2xl border border-white/[0.08] text-center flex flex-col items-center justify-center min-h-[300px] animate-pulse ${className}`}
    >
      <div className="p-4 rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mb-4 shadow-lg shadow-cyan-500/10">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
      <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
      <p className="text-xs text-slate-400 mt-2 max-w-md leading-relaxed">{message}</p>
    </div>
  );
}
