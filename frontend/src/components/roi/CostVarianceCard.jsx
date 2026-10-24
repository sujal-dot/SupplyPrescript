import React from 'react';
import { DollarSign, ArrowUpRight, ArrowDownRight, Minus, AlertCircle } from 'lucide-react';

export default function CostVarianceCard({ cost = {}, currency = 'USD' }) {
  const {
    predicted_cost,
    actual_cost,
    cost_difference,
    cost_variance_percentage,
    money_saved_vs_prediction,
    baseline_cost,
    money_saved_vs_baseline,
  } = cost;

  const formatMoney = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}$${Math.abs(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const costDiffNum = cost_difference != null ? Number(cost_difference) : null;
  const isOverrun = costDiffNum != null && costDiffNum > 0;
  const isSavings = costDiffNum != null && costDiffNum < 0;

  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
            Cost Difference & Variance
          </span>
          <span className="text-xs text-slate-400">Actual vs Predicted</span>
        </div>
        <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
          <DollarSign className="h-4 w-4" />
        </div>
      </div>

      <div>
        <div className="text-xl font-mono font-bold text-white flex items-center space-x-1">
          <span>{formatMoney(cost_difference)}</span>
          <span className="text-xs text-slate-400 font-normal">{currency}</span>
        </div>

        <div className="text-xs font-mono mt-1 flex items-center space-x-1.5">
          {costDiffNum != null ? (
            isOverrun ? (
              <span className="text-amber-300 flex items-center space-x-0.5">
                <ArrowUpRight className="h-3.5 w-3.5" />
                <span>
                  Overrun {cost_variance_percentage != null ? `(+${cost_variance_percentage}%)` : ''}
                </span>
              </span>
            ) : isSavings ? (
              <span className="text-emerald-300 flex items-center space-x-0.5">
                <ArrowDownRight className="h-3.5 w-3.5" />
                <span>
                  Under budget {cost_variance_percentage != null ? `(${cost_variance_percentage}%)` : ''}
                </span>
              </span>
            ) : (
              <span className="text-slate-400 flex items-center space-x-0.5">
                <Minus className="h-3.5 w-3.5" />
                <span>Exact match (0%)</span>
              </span>
            )
          ) : (
            <span className="text-slate-500 italic">Actual cost pending</span>
          )}
        </div>
      </div>

      <div className="pt-2 border-t border-white/[0.06] space-y-1 text-[11px] font-mono">
        <div className="flex items-center justify-between text-slate-400">
          <span>Money saved vs prediction:</span>
          <span className={Number(money_saved_vs_prediction) >= 0 ? 'text-emerald-300' : 'text-amber-300'}>
            {formatMoney(money_saved_vs_prediction)}
          </span>
        </div>

        <div className="flex items-center justify-between text-slate-400">
          <span title="Verified savings vs documented shipment baseline">Money saved vs baseline:</span>
          {money_saved_vs_baseline != null ? (
            <span className={Number(money_saved_vs_baseline) >= 0 ? 'text-emerald-300' : 'text-amber-300'}>
              {formatMoney(money_saved_vs_baseline)}
            </span>
          ) : (
            <span className="text-slate-500 italic">N/A (No baseline)</span>
          )}
        </div>
      </div>
    </div>
  );
}
