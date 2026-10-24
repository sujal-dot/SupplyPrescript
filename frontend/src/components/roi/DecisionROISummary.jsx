import React from 'react';
import {
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Info,
  DollarSign,
  ShieldCheck,
  RefreshCw,
  Layers,
} from 'lucide-react';
import DecisionSuccessBadge from './DecisionSuccessBadge';
import DecisionROICards from './DecisionROICards';
import CostVarianceCard from './CostVarianceCard';
import DeliveryVarianceCard from './DeliveryVarianceCard';
import ROIBreakdown from './ROIBreakdown';
import DecisionROITable from './DecisionROITable';

export default function DecisionROISummary({
  roiData,
  comparison = null,
  loading = false,
  error = null,
  onRefresh = null,
}) {
  if (loading) {
    return (
      <div className="p-8 text-center text-xs text-slate-400 space-y-2">
        <RefreshCw className="h-5 w-5 animate-spin mx-auto text-red-400" />
        <p>Calculating decision ROI and evaluating operational performance...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
        <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
        <span>{error}</span>
      </div>
    );
  }

  if (!roiData) {
    return (
      <div className="p-8 text-center flex flex-col items-center justify-center rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <div className="p-3 rounded-2xl bg-white/[0.04] text-slate-400 mb-2 border border-white/[0.06]">
          <TrendingUp className="h-6 w-6" />
        </div>
        <h4 className="text-sm font-bold text-white">No Decision ROI Data</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1">
          Select an authorized decision to compute ROI metrics, variance, and operational success.
        </p>
      </div>
    );
  }

  const {
    decision_id,
    shipment_id,
    currency = 'USD',
    cost = {},
    delivery = {},
    roi = {},
    decision_evaluation = {},
    calculation_version = '1.0',
    notes = [],
  } = roiData;

  const isPendingOutcome = decision_evaluation.decision_success === 'PENDING_REVIEW';

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* 1. Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <TrendingUp className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                Decision ROI Engine & Success Analytics
              </h3>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-white/[0.06] text-slate-300 border border-white/[0.08]">
                {decision_id}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Target Shipment: <span className="font-mono text-white">{shipment_id || '—'}</span> • Currency: <span className="font-mono text-red-300">{currency}</span> • Version: <span className="font-mono text-slate-300">v{calculation_version}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <DecisionSuccessBadge status={decision_evaluation.decision_success} size="md" />

          {onRefresh && (
            <button
              onClick={onRefresh}
              aria-label="Refresh ROI metrics"
              className="p-1.5 rounded-lg border border-white/[0.08] hover:bg-white/[0.06] text-slate-300 transition-colors"
              title="Refresh ROI Analytics"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* 2. Success Evaluation Explanation Card */}
      <div className="p-3.5 rounded-xl bg-slate-900/80 border border-white/[0.08] flex items-start space-x-3">
        <Info className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold text-white font-mono uppercase tracking-wider">
              Decision Success Evaluation
            </span>
            <span className="text-[10px] font-mono px-2 py-0.2 rounded bg-white/[0.06] text-slate-400">
              {decision_evaluation.policy_is_provisional ? 'Provisional Evaluation Policy' : 'Configured Policy'}
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {decision_evaluation.success_reason || 'Multi-dimensional evaluation across cost, schedule, constraints, and fulfillment.'}
          </p>
        </div>
      </div>

      {/* 3. High-Level ROI Cards (8 metrics) */}
      <DecisionROICards roiData={roiData} />

      {/* 4. Detailed Dimension Cards: Cost Variance & Delivery Variance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CostVarianceCard cost={cost} currency={currency} />
        <DeliveryVarianceCard delivery={delivery} />
      </div>

      {/* 5. Detailed Parameter Comparison Table */}
      <DecisionROITable roiData={roiData} comparison={comparison} />

      {/* 6. Return on Investment (ROI) Formula & Breakdown */}
      <ROIBreakdown roi={roi} currency={currency} />

      {/* 7. Multi-Dimensional Performance Diagnostics */}
      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
            Evaluation Dimensions Breakdown
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            Independent Diagnostic Scores
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-xs font-mono">
          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-400 block">Cost Performance</span>
            <span className="font-bold text-slate-200 mt-1 block">
              {decision_evaluation.cost_performance || 'UNKNOWN'}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-400 block">Delivery Performance</span>
            <span className="font-bold text-slate-200 mt-1 block">
              {decision_evaluation.delivery_performance || 'UNKNOWN'}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-400 block">Constraint Compliance</span>
            <span className={`font-bold mt-1 block ${decision_evaluation.constraint_compliance === 'FAIL' ? 'text-rose-400' : 'text-emerald-300'}`}>
              {decision_evaluation.constraint_compliance || 'UNKNOWN'}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-400 block">Quantity Fulfillment</span>
            <span className="font-bold text-slate-200 mt-1 block">
              {decision_evaluation.quantity_performance || 'UNKNOWN'}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-400 block">Data Completeness</span>
            <span className="font-bold text-red-300 mt-1 block">
              {decision_evaluation.data_completeness || 'INSUFFICIENT'}
            </span>
          </div>
        </div>
      </div>

      {/* Operational Notes if any */}
      {notes && notes.length > 0 && (
        <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 text-xs text-slate-400 space-y-1">
          <span className="font-mono text-[10px] text-slate-500 uppercase block font-bold">Accounting Notes:</span>
          <ul className="list-disc list-inside space-y-0.5">
            {notes.map((note, idx) => (
              <li key={idx} className="text-[11px] text-slate-400 font-mono">
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
