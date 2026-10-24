import React from 'react';
import { Clock, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export default function DeliveryVarianceCard({ delivery = {} }) {
  const { predicted_delay, actual_delay, delay_difference } = delivery;

  const formatDays = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}${Math.abs(num).toFixed(1)} days`;
  };

  const diffNum = delay_difference != null ? Number(delay_difference) : null;
  const isWorse = diffNum != null && diffNum > 0;
  const isBetter = diffNum != null && diffNum < 0;

  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
            Delay Difference
          </span>
          <span className="text-xs text-slate-400">Actual vs Predicted Delay</span>
        </div>
        <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
          <Clock className="h-4 w-4" />
        </div>
      </div>

      <div>
        <div className="text-xl font-mono font-bold text-white">
          {formatDays(delay_difference)}
        </div>

        <div className="text-xs font-mono mt-1 flex items-center space-x-1.5">
          {diffNum != null ? (
            isWorse ? (
              <span className="text-amber-300 flex items-center space-x-0.5">
                <ArrowUpRight className="h-3.5 w-3.5" />
                <span>Later than predicted (+{diffNum}d)</span>
              </span>
            ) : isBetter ? (
              <span className="text-emerald-300 flex items-center space-x-0.5">
                <ArrowDownRight className="h-3.5 w-3.5" />
                <span>Earlier than predicted ({diffNum}d)</span>
              </span>
            ) : (
              <span className="text-slate-400 flex items-center space-x-0.5">
                <Minus className="h-3.5 w-3.5" />
                <span>Matched prediction</span>
              </span>
            )
          ) : (
            <span className="text-slate-500 italic">Actual delay pending delivery</span>
          )}
        </div>
      </div>

      <div className="pt-2 border-t border-white/[0.06] space-y-1 text-[11px] font-mono">
        <div className="flex items-center justify-between text-slate-400">
          <span>Predicted delay:</span>
          <span className="text-slate-200">
            {predicted_delay != null ? `${Number(predicted_delay).toFixed(1)} days` : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>Actual delay:</span>
          <span className="text-slate-200">
            {actual_delay != null ? `${Number(actual_delay).toFixed(1)} days` : 'Pending'}
          </span>
        </div>
      </div>
    </div>
  );
}
