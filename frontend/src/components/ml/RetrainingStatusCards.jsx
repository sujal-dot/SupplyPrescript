import React from 'react';
import {
  Cpu,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sliders,
  Layers,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

export default function RetrainingStatusCards({
  monitorStatus = {},
  jobCounts = {},
  loading = false,
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="glass-card p-4 rounded-xl animate-pulse h-28 flex flex-col justify-between">
            <div className="h-4 w-20 bg-white/10 rounded" />
            <div className="h-7 w-28 bg-white/10 rounded" />
            <div className="h-3 w-16 bg-white/5 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const m = monitorStatus || {};
  const status = m.status || 'INSUFFICIENT_DATA';
  const isDegraded = m.is_degraded === true;
  const sampleCount = m.evaluated_sample_count ?? 0;
  const minThreshold = m.min_sample_threshold ?? 10;
  const activeVersion = m.model_version || 'v1.0';

  const baseMae = m.baseline_metrics?.mae != null ? Number(m.baseline_metrics.mae) : null;
  const liveMae = m.current_metrics?.mae != null ? Number(m.current_metrics.mae) : null;
  const maeDeltaPct = m.current_metrics?.mae_delta_pct != null ? Number(m.current_metrics.mae_delta_pct) : null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {/* 1. Production Model & Active Version */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-red-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Active Production Model</span>
          <Cpu className="h-4 w-4 text-red-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-red-400 tracking-tight">
          {activeVersion}
        </div>
        <div className="text-[11px] text-slate-400 mt-1 flex items-center space-x-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse inline-block" />
          <span>Serving live predictions</span>
        </div>
      </div>

      {/* 2. Monitor Drift & Degradation Status */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-emerald-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Performance Drift Monitor</span>
          <Activity className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="text-xl font-bold font-mono tracking-tight flex items-center space-x-2">
          {status === 'HEALTHY' ? (
            <span className="text-emerald-400 flex items-center space-x-1.5">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 inline" />
              <span>Healthy</span>
            </span>
          ) : status === 'DEGRADED' ? (
            <span className="text-rose-400 flex items-center space-x-1.5">
              <AlertTriangle className="h-5 w-5 text-rose-400 inline" />
              <span>Degraded</span>
            </span>
          ) : (
            <span className="text-amber-400 flex items-center space-x-1.5">
              <Clock className="h-5 w-5 text-amber-400 inline" />
              <span>Insufficient Data</span>
            </span>
          )}
        </div>
        <div className="text-[11px] text-slate-400 mt-1 truncate" title={m.trigger_reason || ''}>
          {status === 'INSUFFICIENT_DATA'
            ? `${sampleCount} / ${minThreshold} samples needed`
            : status === 'HEALTHY'
            ? 'Within configured tolerance'
            : 'Performance degraded beyond threshold'}
        </div>
      </div>

      {/* 3. Live MAE vs Baseline */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-violet-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Baseline vs Live MAE</span>
          <Sliders className="h-4 w-4 text-violet-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-white tracking-tight">
          {liveMae != null ? `${liveMae.toFixed(2)} d` : (baseMae != null ? `${baseMae.toFixed(2)} d` : '—')}
        </div>
        <div className="text-[11px] text-slate-400 mt-1 flex items-center space-x-1">
          {maeDeltaPct != null ? (
            <span className={maeDeltaPct > 0 ? 'text-rose-400' : 'text-emerald-400'}>
              {maeDeltaPct > 0 ? `+${maeDeltaPct.toFixed(1)}%` : `${maeDeltaPct.toFixed(1)}%`} vs baseline
            </span>
          ) : (
            <span>Baseline: {baseMae != null ? `${baseMae.toFixed(2)} d` : '2.04 d'}</span>
          )}
        </div>
      </div>

      {/* 4. Retraining Policy & Safeguard */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-red-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Promotion Policy</span>
          <ShieldCheck className="h-4 w-4 text-red-400" />
        </div>
        <div className="text-xl font-bold font-mono text-white tracking-tight">
          Controlled Sign-Off
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>Candidate validation required</span>
        </div>
      </div>
    </div>
  );
}
