import React from 'react';
import {
  Sparkles,
  CheckCircle2,
  Clock,
  XCircle,
  Target,
  Compass,
  Cpu,
  Database,
} from 'lucide-react';

export default function FeedbackSummaryCards({
  summary = {},
  activeModelVersion = 'v1.0.0',
  datasetVersion = null,
  loading = false,
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="glass-card p-4 rounded-xl animate-pulse h-28 flex flex-col justify-between">
            <div className="h-4 w-20 bg-white/10 rounded" />
            <div className="h-7 w-28 bg-white/10 rounded" />
            <div className="h-3 w-16 bg-white/5 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const s = summary || {};
  const total = s.total ?? 0;
  const eligible = s.eligible ?? 0;
  const pending = s.pending_outcome ?? 0;
  const excluded = s.excluded ?? 0;
  const underReview = s.under_review ?? 0;
  const mae = s.mean_absolute_error != null ? Number(s.mean_absolute_error) : null;
  const bias = s.mean_signed_error != null ? Number(s.mean_signed_error) : null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {/* 1. Total Stored Predictions */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-red-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Total Predictions</span>
          <Sparkles className="h-4 w-4 text-red-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-white tracking-tight">
          {total.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>Persisted ML predictions</span>
        </div>
      </div>

      {/* 2. Eligible Feedback Records */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-emerald-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Eligible Records</span>
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
          {eligible.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>Verified delivery actuals</span>
        </div>
      </div>

      {/* 3. Pending Outcomes */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-amber-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Pending Actuals</span>
          <Clock className="h-4 w-4 text-amber-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-amber-400 tracking-tight">
          {pending.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>Shipments in transit</span>
        </div>
      </div>

      {/* 4. Excluded / Under Review */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-rose-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Excluded Records</span>
          <XCircle className="h-4 w-4 text-rose-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-rose-400 tracking-tight">
          {excluded.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          {underReview > 0 ? (
            <span className="text-violet-400">+{underReview} under review</span>
          ) : (
            <span>Data quality or cancelled</span>
          )}
        </div>
      </div>

      {/* 5. Mean Absolute Delay Error (MAE) */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-rose-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Delay MAE</span>
          <Target className="h-4 w-4 text-rose-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-white tracking-tight">
          {mae != null ? `${mae.toFixed(2)} d` : <span className="text-slate-500 text-lg font-normal">N/A</span>}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>Average delay miss (days)</span>
        </div>
      </div>

      {/* 6. Mean Signed Error (Directional Bias) */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-violet-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Directional Bias</span>
          <Compass className="h-4 w-4 text-violet-400" />
        </div>
        <div className="text-2xl font-bold font-mono tracking-tight">
          {bias != null ? (
            <span className={bias > 0 ? 'text-rose-400' : 'text-emerald-400'}>
              {bias > 0 ? `+${bias.toFixed(2)}` : bias.toFixed(2)} d
            </span>
          ) : (
            <span className="text-slate-500 text-lg font-normal">N/A</span>
          )}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          {bias != null ? (
            bias > 0 ? 'Under-predicted (arrived late)' : 'Over-predicted (arrived early)'
          ) : (
            'Evaluated actuals pending'
          )}
        </div>
      </div>

      {/* 7. Active Model Version */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-red-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Model Version</span>
          <Cpu className="h-4 w-4 text-red-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-red-400 tracking-tight truncate">
          {activeModelVersion}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>XGBoost dual predictor</span>
        </div>
      </div>

      {/* 8. Feedback Dataset Version */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-emerald-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Dataset Snapshot</span>
          <Database className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="text-lg font-bold font-mono text-emerald-300 tracking-tight truncate" title={datasetVersion || 'Live Database'}>
          {datasetVersion ? datasetVersion.replace('FB_DS_', '') : 'Live Pipeline'}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>Deterministic manifest</span>
        </div>
      </div>
    </div>
  );
}
