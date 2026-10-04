import React from 'react';
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react';

export default function StatusCard({ title, status, details, loading, onRefresh }) {
  const isHealthy = status === 'healthy' || status === 'connected';

  return (
    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6 shadow-xl backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </h3>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1 text-slate-400 hover:text-cyan-400 transition-colors disabled:opacity-50"
            title="Refresh status"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>

      <div className="flex items-center space-x-3 mb-3">
        {loading ? (
          <div className="h-4 w-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        ) : isHealthy ? (
          <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
        ) : (
          <XCircle className="h-6 w-6 text-rose-400 shrink-0" />
        )}
        <div className="text-xl font-bold capitalize">
          {loading ? (
            <span className="text-slate-400 text-base">Checking status...</span>
          ) : (
            <span className={isHealthy ? 'text-emerald-400' : 'text-rose-400'}>
              {status || 'Unknown'}
            </span>
          )}
        </div>
      </div>

      {details && (
        <div className="text-xs font-mono bg-slate-900/60 p-2.5 rounded border border-slate-800 text-slate-400 overflow-x-auto">
          {typeof details === 'object' ? JSON.stringify(details, null, 2) : details}
        </div>
      )}
    </div>
  );
}
