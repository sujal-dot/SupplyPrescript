import React from 'react';
import {
  FileText,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  Scale,
  ShieldCheck,
  Percent,
  HelpCircle,
} from 'lucide-react';

export default function ROISummaryCards({
  summary = null,
  currency = 'USD',
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
  const totalDecisions = s.total_decisions ?? 0;
  const completedDecisions = s.completed_decisions ?? 0;
  const pendingDecisions = s.pending_decisions ?? 0;
  const successfulDecisions = s.successful_decisions ?? 0;
  const failedDecisions = s.failed_decisions ?? 0;
  const partialDecisions = s.partially_successful_decisions ?? 0;
  const eligibleCompleted = s.eligible_completed_decisions ?? 0;

  const successRate = s.success_rate != null ? Number(s.success_rate) : null;
  const avgCostDiff = s.average_cost_difference != null ? Number(s.average_cost_difference) : null;
  const verifiedBaselineSavings = s.verified_baseline_savings != null ? Number(s.verified_baseline_savings) : null;
  const aggregateROI = s.aggregate_roi || {};

  // Cost difference color logic
  // Negative cost difference means actual was LOWER than predicted (favorable savings)
  // Positive cost difference means cost overrun
  let costDiffColor = 'text-slate-300';
  let costDiffSign = '';
  if (avgCostDiff != null) {
    if (avgCostDiff < 0) {
      costDiffColor = 'text-emerald-400';
      costDiffSign = '-';
    } else if (avgCostDiff > 0) {
      costDiffColor = 'text-rose-400';
      costDiffSign = '+';
    }
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {/* 1. Total Decisions */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-red-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Total Decisions</span>
          <FileText className="h-4 w-4 text-red-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-white tracking-tight">
          {totalDecisions.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1 flex items-center space-x-1">
          <span>In active filter scope</span>
        </div>
      </div>

      {/* 2. Completed Decisions With Actual Outcomes */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-rose-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Completed Decisions</span>
          <CheckCircle2 className="h-4 w-4 text-rose-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-white tracking-tight">
          {completedDecisions.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
          <span>With recorded actuals</span>
          <span className="text-amber-400 font-mono">({pendingDecisions} pending)</span>
        </div>
      </div>

      {/* 3. Successful Decisions */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-emerald-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Successful Decisions</span>
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
          {successfulDecisions.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          {partialDecisions > 0 ? (
            <span className="text-amber-300">+{partialDecisions} partially successful</span>
          ) : (
            <span>Met cost & delivery targets</span>
          )}
        </div>
      </div>

      {/* 4. Failed Decisions */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-rose-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Failed Decisions</span>
          <XCircle className="h-4 w-4 text-rose-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-rose-400 tracking-tight">
          {failedDecisions.toLocaleString()}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          <span>Overrun &gt;15% or delay &gt;2d</span>
        </div>
      </div>

      {/* 5. Decision Success Rate */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-red-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Decision Success Rate</span>
          <Percent className="h-4 w-4 text-red-400" />
        </div>
        <div className="text-2xl font-bold font-mono tracking-tight">
          {successRate != null ? (
            <span className={successRate >= 75 ? 'text-emerald-400' : successRate >= 50 ? 'text-amber-400' : 'text-rose-400'}>
              {successRate.toFixed(1)}%
            </span>
          ) : (
            <span className="text-slate-400 text-lg font-normal">N/A</span>
          )}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          {eligibleCompleted > 0 ? (
            <span>Denominator: {eligibleCompleted} completed</span>
          ) : (
            <span title="Pending decisions excluded">Pending actual outcomes</span>
          )}
        </div>
      </div>

      {/* 6. Average Cost Difference */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-rose-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Avg Cost Difference</span>
          <Scale className="h-4 w-4 text-rose-400" />
        </div>
        <div className={`text-2xl font-bold font-mono tracking-tight ${costDiffColor}`}>
          {avgCostDiff != null ? (
            <>
              {costDiffSign}${Math.abs(avgCostDiff).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </>
          ) : (
            <span className="text-slate-400 text-lg font-normal">N/A</span>
          )}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          {avgCostDiff != null ? (
            avgCostDiff <= 0 ? 'Actual cost below prediction' : 'Cost overrun vs prediction'
          ) : (
            'No comparable cost records'
          )}
        </div>
      </div>

      {/* 7. Verified Baseline Savings */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-emerald-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Baseline Savings</span>
          <TrendingUp className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
          {verifiedBaselineSavings != null ? (
            `$${verifiedBaselineSavings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          ) : (
            <span className="text-slate-400 text-lg font-normal">N/A</span>
          )}
        </div>
        <div className="text-[11px] text-slate-400 mt-1">
          {verifiedBaselineSavings != null ? (
            'Verified vs documented baseline'
          ) : (
            'Documented baselines pending'
          )}
        </div>
      </div>

      {/* 8. ROI Status or Aggregate ROI */}
      <div className="glass-card p-4 rounded-xl border border-white/[0.08] relative overflow-hidden group hover:border-violet-500/30 transition-all">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-xs font-medium uppercase tracking-wider">Aggregate ROI</span>
          <TrendingUp className="h-4 w-4 text-violet-400" />
        </div>
        <div className="text-2xl font-bold font-mono tracking-tight">
          {aggregateROI.status === 'CALCULATED' && aggregateROI.roi_percentage != null ? (
            <span className="text-emerald-400">
              {aggregateROI.roi_percentage > 0 ? '+' : ''}{aggregateROI.roi_percentage.toFixed(1)}%
            </span>
          ) : (
            <span className="text-slate-400 text-lg font-normal">N/A</span>
          )}
        </div>
        <div className="text-[11px] text-slate-400 mt-1 truncate" title={aggregateROI.reason || 'Documented incremental denominator needed'}>
          {aggregateROI.status === 'CALCULATED' ? (
            'Weighted net benefit / investment'
          ) : (
            <span className="text-amber-400/90">Investment base unavailable</span>
          )}
        </div>
      </div>
    </div>
  );
}
