import React from 'react';
import { DollarSign, Clock, TrendingUp, ShieldCheck, CheckCircle2, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import DecisionSuccessBadge from './DecisionSuccessBadge';

export default function DecisionROICards({ roiData = {} }) {
  const { cost = {}, delivery = {}, roi = {}, decision_evaluation = {}, currency = 'USD' } = roiData;

  const formatMoney = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}$${Math.abs(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatRawMoney = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDays = (val) => {
    if (val == null) return '—';
    return `${Number(val).toFixed(1)}d`;
  };

  const costDiff = cost?.cost_difference != null ? Number(cost.cost_difference) : null;
  const delayDiff = delivery?.delay_difference != null ? Number(delivery.delay_difference) : null;
  const isCalculatedROI = roi?.status === 'CALCULATED' && roi?.roi_percentage != null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {/* 1. Predicted Cost */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
          Predicted Cost
        </span>
        <div className="mt-1">
          <div className="text-base font-mono font-bold text-white">
            {formatRawMoney(cost.predicted_cost)}
          </div>
          <span className="text-[10px] text-slate-400 font-mono">Original optimization snapshot</span>
        </div>
      </div>

      {/* 2. Actual Cost */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
          Actual Cost
        </span>
        <div className="mt-1">
          <div className="text-base font-mono font-bold text-white">
            {cost.actual_cost != null ? formatRawMoney(cost.actual_cost) : <span className="text-slate-500 italic text-xs">Pending actuals</span>}
          </div>
          <span className="text-[10px] text-slate-400 font-mono">Verified operational outcome</span>
        </div>
      </div>

      {/* 3. Cost Difference */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
          Cost Difference
        </span>
        <div className="mt-1">
          <div className="text-base font-mono font-bold text-white flex items-center space-x-1">
            <span>{formatMoney(cost.cost_difference)}</span>
            {costDiff != null && (
              <span className={`text-xs ${costDiff > 0 ? 'text-amber-300' : costDiff < 0 ? 'text-emerald-300' : 'text-slate-400'}`}>
                {costDiff > 0 ? <ArrowUpRight className="h-3 w-3 inline" /> : costDiff < 0 ? <ArrowDownRight className="h-3 w-3 inline" /> : <Minus className="h-3 w-3 inline" />}
              </span>
            )}
          </div>
          <span className="text-[10px] text-slate-400 font-mono">
            {cost.cost_variance_percentage != null ? `${cost.cost_variance_percentage}% variance` : 'Actual - Predicted'}
          </span>
        </div>
      </div>

      {/* 4. Money Saved */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400" title="Predicted Cost minus Actual Cost (vs Prediction), or Baseline minus Actual (vs Baseline)">
          Money Saved
        </span>
        <div className="mt-1">
          <div className="text-base font-mono font-bold">
            {cost.money_saved_vs_baseline != null ? (
              <span className={Number(cost.money_saved_vs_baseline) >= 0 ? 'text-emerald-300' : 'text-amber-300'}>
                {formatMoney(cost.money_saved_vs_baseline)}
              </span>
            ) : cost.money_saved_vs_prediction != null ? (
              <span className={Number(cost.money_saved_vs_prediction) >= 0 ? 'text-emerald-300' : 'text-amber-300'}>
                {formatMoney(cost.money_saved_vs_prediction)}
              </span>
            ) : (
              <span className="text-slate-500 italic text-xs">Pending outcome</span>
            )}
          </div>
          <span className="text-[10px] text-slate-400 font-mono">
            {cost.money_saved_vs_baseline != null ? 'vs Baseline alternative' : 'vs Optimization forecast'}
          </span>
        </div>
      </div>

      {/* 5. Predicted Delay */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
          Predicted Delay
        </span>
        <div className="mt-1">
          <div className="text-base font-mono font-bold text-white">
            {delivery.predicted_delay != null ? `${formatDays(delivery.predicted_delay)} delay` : '—'}
          </div>
          <span className="text-[10px] text-slate-400 font-mono">Forecast schedule impact</span>
        </div>
      </div>

      {/* 6. Actual Delay */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
          Actual Delay
        </span>
        <div className="mt-1">
          <div className="text-base font-mono font-bold text-white">
            {delivery.actual_delay != null ? `${formatDays(delivery.actual_delay)} delay` : <span className="text-slate-500 italic text-xs">Pending delivery</span>}
          </div>
          <span className="text-[10px] text-slate-400 font-mono">
            {delayDiff != null ? (delayDiff < 0 ? `${delayDiff}d earlier` : delayDiff > 0 ? `+${delayDiff}d later` : 'On schedule') : 'Carrier delivery milestone'}
          </span>
        </div>
      </div>

      {/* 7. Decision Success */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
          Decision Success
        </span>
        <div className="mt-1">
          <DecisionSuccessBadge status={decision_evaluation.decision_success} size="sm" />
          <div className="text-[10px] text-slate-400 font-mono mt-1 line-clamp-1">
            {decision_evaluation.data_completeness || 'EVALUATION'}
          </div>
        </div>
      </div>

      {/* 8. ROI */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
          Decision ROI
        </span>
        <div className="mt-1">
          <div className="text-base font-mono font-bold">
            {isCalculatedROI ? (
              <span className={roi.roi_percentage >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                {roi.roi_percentage > 0 ? `+${roi.roi_percentage}%` : `${roi.roi_percentage}%`}
              </span>
            ) : (
              <span className="text-slate-400 font-mono text-sm">N/A</span>
            )}
          </div>
          <span className="text-[10px] text-slate-400 font-mono truncate block" title={roi?.reason || 'Baseline required'}>
            {roi?.status === 'CALCULATED' ? 'Incremental Benefit / Investment' : 'Baseline denominator required'}
          </span>
        </div>
      </div>
    </div>
  );
}
