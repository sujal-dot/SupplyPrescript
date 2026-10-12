import React from 'react';
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react';

export default function StatusCard({ title, status, details, loading, onRefresh }) {
  const isHealthy = status === 'healthy' || status === 'connected';

  return (
    <div className="glass-card-interactive rounded-2xl p-6 relative overflow-hidden group">
      {/* Subtle contextual ambient back-glow */}
      <div 
        className={`absolute -top-16 -right-16 w-36 h-36 rounded-full blur-3xl pointer-events-none transition-opacity duration-500 ${
          isHealthy ? 'bg-emerald-500/15 group-hover:bg-emerald-500/25' : 'bg-rose-500/15 group-hover:bg-rose-500/25'
        }`} 
      />

      <div className="flex items-center justify-between mb-4 relative z-10">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300/80">
          {title}
        </h3>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-300 hover:bg-white/[0.06] border border-transparent hover:border-white/10 transition-all duration-200 disabled:opacity-50"
            title="Refresh status"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        )}
      </div>

      <div className="flex items-center space-x-3 mb-4 relative z-10">
        {loading ? (
          <div className="h-6 w-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin shrink-0 shadow-lg shadow-cyan-500/30" />
        ) : isHealthy ? (
          <div className="p-1 rounded-full bg-emerald-500/15 border border-emerald-400/30 shadow-md shadow-emerald-500/20 shrink-0">
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          </div>
        ) : (
          <div className="p-1 rounded-full bg-rose-500/15 border border-rose-400/30 shadow-md shadow-rose-500/20 shrink-0">
            <XCircle className="h-5 w-5 text-rose-400" />
          </div>
        )}

        <div className="text-xl font-bold capitalize">
          {loading ? (
            <span className="text-slate-400 text-base font-normal">Verifying telemetry...</span>
          ) : (
            <span className={isHealthy ? 'text-emerald-300 font-semibold drop-shadow-sm' : 'text-rose-300 font-semibold'}>
              {status || 'Unknown'}
            </span>
          )}
        </div>
      </div>

      {details && (
        <div className="relative z-10">
          <div className="text-[11px] font-mono glass-code p-3.5 rounded-xl text-slate-300 overflow-x-auto border border-white/[0.06]">
            {typeof details === 'object' ? JSON.stringify(details, null, 2) : details}
          </div>
        </div>
      )}
    </div>
  );
}
