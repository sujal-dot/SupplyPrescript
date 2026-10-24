import React from 'react';
import { DollarSign, Clock, Calendar, Package, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export default function OutcomeVarianceCards({ variance = {}, predicted = {}, actual = {} }) {
  const costVar = variance?.cost_variance;
  const costPct = variance?.cost_variance_percentage;
  const delayVar = variance?.delay_variance;
  const dateVar = variance?.delivery_date_variance_days;
  const qtyVar = variance?.quantity_variance;

  const formatCurrency = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}$${Math.abs(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDays = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}${Math.abs(num).toFixed(1)} days`;
  };

  const formatUnits = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}${Math.abs(num).toLocaleString()} units`;
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {/* 1. Cost Variance Card */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Cost Variance</span>
          <div className="p-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
            <DollarSign className="h-3.5 w-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className="text-base font-mono font-bold text-white">
            {formatCurrency(costVar)}
          </div>
          <div className="text-[11px] font-mono mt-0.5 flex items-center space-x-1">
            {costVar != null ? (
              costVar > 0 ? (
                <span className="text-amber-300 flex items-center space-x-0.5">
                  <ArrowUpRight className="h-3 w-3" />
                  <span>+{costPct != null ? `${costPct}%` : 'Over budget'}</span>
                </span>
              ) : costVar < 0 ? (
                <span className="text-emerald-300 flex items-center space-x-0.5">
                  <ArrowDownRight className="h-3 w-3" />
                  <span>{costPct != null ? `${costPct}%` : 'Cost savings'}</span>
                </span>
              ) : (
                <span className="text-slate-400 flex items-center space-x-0.5">
                  <Minus className="h-3 w-3" />
                  <span>On target (0%)</span>
                </span>
              )
            ) : (
              <span className="text-slate-500">Actual cost pending</span>
            )}
          </div>
        </div>
      </div>

      {/* 2. Delay Variance Card */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Delay Variance</span>
          <div className="p-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
            <Clock className="h-3.5 w-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className="text-base font-mono font-bold text-white">
            {formatDays(delayVar)}
          </div>
          <div className="text-[11px] font-mono mt-0.5">
            {delayVar != null ? (
              delayVar > 0 ? (
                <span className="text-amber-300">Later than predicted</span>
              ) : delayVar < 0 ? (
                <span className="text-emerald-300">Earlier than predicted</span>
              ) : (
                <span className="text-slate-400">Matched prediction</span>
              )
            ) : (
              <span className="text-slate-500">Delay pending delivery</span>
            )}
          </div>
        </div>
      </div>

      {/* 3. Delivery Date Variance */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Milestone Date Diff</span>
          <div className="p-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
            <Calendar className="h-3.5 w-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className="text-base font-mono font-bold text-white">
            {dateVar != null ? `${dateVar > 0 ? '+' : ''}${dateVar} days` : '—'}
          </div>
          <div className="text-[11px] font-mono mt-0.5">
            {dateVar != null ? (
              dateVar > 0 ? (
                <span className="text-amber-300">{`${dateVar} days late`}</span>
              ) : dateVar < 0 ? (
                <span className="text-emerald-300">{`${Math.abs(dateVar)} days early`}</span>
              ) : (
                <span className="text-slate-400">Arrived on scheduled day</span>
              )
            ) : (
              <span className="text-slate-500">Date pending</span>
            )}
          </div>
        </div>
      </div>

      {/* 4. Quantity Variance Card */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Quantity Variance</span>
          <div className="p-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
            <Package className="h-3.5 w-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className="text-base font-mono font-bold text-white">
            {formatUnits(qtyVar)}
          </div>
          <div className="text-[11px] font-mono mt-0.5">
            {qtyVar != null ? (
              qtyVar === 0 ? (
                <span className="text-slate-300">100% quantity delivered</span>
              ) : qtyVar < 0 ? (
                <span className="text-amber-300">Partial delivery shortage</span>
              ) : (
                <span className="text-rose-300">Over-delivery</span>
              )
            ) : (
              <span className="text-slate-500">Quantity pending</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
