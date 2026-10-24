import React from 'react';
import { DollarSign, TrendingDown, TrendingUp, Sparkles, HelpCircle } from 'lucide-react';

export default function CostComparison({
  baseline = null,
  alternatives = [],
  recommendedOptionId = null,
}) {
  if (!baseline && (!alternatives || alternatives.length === 0)) {
    return null;
  }

  const formatCurrency = (val) => {
    if (val == null || isNaN(val)) return '—';
    return `$${Number(val).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDelta = (val, pct) => {
    if (val == null || isNaN(val)) return '—';
    const num = Number(val);
    if (Math.abs(num) < 0.01) return '$0.00 (0.0%)';
    const sign = num > 0 ? '+' : '';
    const pctStr = pct != null ? ` (${sign}${Number(pct).toFixed(1)}%)` : '';
    return `${sign}$${num.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}${pctStr}`;
  };

  // Extract baseline costs
  const baselineProcurement =
    baseline?.unit_cost != null && baseline?.quantity != null
      ? baseline.unit_cost * baseline.quantity
      : baseline?.cost_breakdown?.procurement ?? null;
  const baselineFreight = baseline?.shipping_cost ?? baseline?.cost_breakdown?.shipping ?? null;
  const baselineHolding = baseline?.cost_breakdown?.holding ?? 0;
  const baselineDelayPenalty = baseline?.cost_breakdown?.delay ?? 0;
  const baselineTotal =
    baseline?.estimated_total_cost ??
    (baselineProcurement != null && baselineFreight != null
      ? baselineProcurement + baselineFreight + baselineHolding + baselineDelayPenalty
      : null);

  // Helper to extract option cost items
  const getOptionCost = (opt, key) => {
    if (!opt) return null;
    const bd = opt.cost_breakdown || {};
    if (key === 'procurement') {
      return bd.procurement ?? (opt.unit_cost != null && baseline?.quantity != null ? opt.unit_cost * baseline.quantity : baselineProcurement);
    }
    if (key === 'freight') {
      return bd.shipping ?? bd.freight ?? null;
    }
    if (key === 'holding') {
      return bd.holding ?? 0;
    }
    if (key === 'delay_penalty') {
      return bd.delay ?? bd.delay_penalty ?? 0;
    }
    if (key === 'total') {
      return opt.estimated_total_cost ?? null;
    }
    return null;
  };

  const options = alternatives || [];

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <DollarSign className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Itemized Cost &amp; Impact Matrix
            </h3>
            <p className="text-xs text-slate-400">
              Comparative expenditure breakdown across baseline plan and candidate strategic alternatives
            </p>
          </div>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono uppercase text-[11px]">
              <th className="py-3.5 px-4 font-semibold w-1/4">Cost Component</th>
              <th className="py-3.5 px-4 font-semibold">
                <span className="text-slate-300">Baseline (Current)</span>
              </th>
              {options.map((opt) => {
                const isRec =
                  opt.is_recommended ||
                  opt.option_id === recommendedOptionId ||
                  (recommendedOptionId == null && opt.option_id === 'A');
                return (
                  <th
                    key={opt.option_id}
                    className={`py-3.5 px-4 font-semibold ${
                      isRec ? 'bg-red-500/10 text-red-300' : 'text-slate-300'
                    }`}
                  >
                    <div className="flex items-center space-x-1.5">
                      <span>Option {opt.option_id}: {opt.name || opt.strategy}</span>
                      {isRec && (
                        <span className="p-0.5 rounded bg-red-500/20 text-red-300">
                          <Sparkles className="h-3 w-3" />
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {/* Procurement / Base Cost */}
            <tr className="hover:bg-white/[0.02]">
              <td className="py-3 px-4 font-medium text-slate-300">
                Procurement Cost (Goods)
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {formatCurrency(baselineProcurement)}
              </td>
              {options.map((opt) => (
                <td key={opt.option_id} className="py-3 px-4 font-mono text-slate-200">
                  {formatCurrency(getOptionCost(opt, 'procurement'))}
                </td>
              ))}
            </tr>

            {/* Freight / Shipping */}
            <tr className="hover:bg-white/[0.02]">
              <td className="py-3 px-4 font-medium text-slate-300">
                Logistics &amp; Freight
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {formatCurrency(baselineFreight)}
              </td>
              {options.map((opt) => (
                <td key={opt.option_id} className="py-3 px-4 font-mono text-slate-200">
                  {formatCurrency(getOptionCost(opt, 'freight'))}
                </td>
              ))}
            </tr>

            {/* Holding Cost */}
            <tr className="hover:bg-white/[0.02]">
              <td className="py-3 px-4 font-medium text-slate-300">
                Inventory Holding Buffer
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {formatCurrency(baselineHolding)}
              </td>
              {options.map((opt) => (
                <td key={opt.option_id} className="py-3 px-4 font-mono text-slate-200">
                  {formatCurrency(getOptionCost(opt, 'holding'))}
                </td>
              ))}
            </tr>

            {/* Delay & Risk Penalty */}
            <tr className="hover:bg-white/[0.02]">
              <td className="py-3 px-4 font-medium text-slate-300">
                Delay Penalty / Impact
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {formatCurrency(baselineDelayPenalty)}
              </td>
              {options.map((opt) => (
                <td key={opt.option_id} className="py-3 px-4 font-mono text-slate-200">
                  {formatCurrency(getOptionCost(opt, 'delay_penalty'))}
                </td>
              ))}
            </tr>

            {/* Total Estimated Cost */}
            <tr className="bg-white/[0.03] font-bold border-t border-white/[0.08]">
              <td className="py-3.5 px-4 text-white uppercase font-mono tracking-wider text-[11px]">
                Total Estimated Cost
              </td>
              <td className="py-3.5 px-4 font-mono text-white text-sm">
                {formatCurrency(baselineTotal)}
              </td>
              {options.map((opt) => {
                const total = getOptionCost(opt, 'total');
                const isRec =
                  opt.is_recommended ||
                  opt.option_id === recommendedOptionId ||
                  (recommendedOptionId == null && opt.option_id === 'A');
                return (
                  <td
                    key={opt.option_id}
                    className={`py-3.5 px-4 font-mono text-sm ${
                      isRec ? 'bg-red-500/15 text-red-300' : 'text-white'
                    }`}
                  >
                    {total != null ? formatCurrency(total) : 'Unconfigured'}
                  </td>
                );
              })}
            </tr>

            {/* Cost Delta vs Baseline */}
            <tr className="hover:bg-white/[0.02] text-[11px]">
              <td className="py-3 px-4 font-medium text-slate-400">
                Delta vs Baseline
              </td>
              <td className="py-3 px-4 font-mono text-slate-500">—</td>
              {options.map((opt) => {
                const delta = opt.additional_cost;
                const pct = opt.additional_cost_percentage;
                const isHigher = Number(delta) > 0;
                const isLower = Number(delta) < 0;

                return (
                  <td
                    key={opt.option_id}
                    className={`py-3 px-4 font-mono font-semibold ${
                      isHigher
                        ? 'text-rose-400'
                        : isLower
                        ? 'text-emerald-400'
                        : 'text-slate-400'
                    }`}
                  >
                    {formatDelta(delta, pct)}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
