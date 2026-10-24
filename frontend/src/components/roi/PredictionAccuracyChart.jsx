import React from 'react';
import { Target, AlertCircle, Info, Activity, Clock, DollarSign } from 'lucide-react';

export default function PredictionAccuracyChart({
  accuracy = {},
  currency = 'USD',
  loading = false,
  height = 300,
}) {
  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl animate-pulse flex flex-col justify-between" style={{ height }}>
        <div className="h-5 w-48 bg-white/10 rounded-md" />
        <div className="grid grid-cols-2 gap-4 h-44">
          <div className="bg-white/5 rounded-xl" />
          <div className="bg-white/5 rounded-xl" />
        </div>
        <div className="h-4 w-32 bg-white/10 rounded-md" />
      </div>
    );
  }

  const a = accuracy || {};
  const costEvaluated = a.cost_records_evaluated ?? 0;
  const delayEvaluated = a.delay_records_evaluated ?? 0;

  if (costEvaluated === 0 && delayEvaluated === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col items-center justify-center text-center text-slate-400" style={{ height }}>
        <AlertCircle className="h-8 w-8 text-slate-500 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Accuracy Benchmarks</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          Accuracy error metrics require completed decisions with both predicted values and verified outcomes in {currency}.
        </p>
      </div>
    );
  }

  const costMae = a.cost_mae != null ? Number(a.cost_mae) : null;
  const costMape = a.cost_mape != null ? Number(a.cost_mape) : null;
  const costRmse = a.cost_rmse != null ? Number(a.cost_rmse) : null;
  const costMse = a.cost_mean_signed_error != null ? Number(a.cost_mean_signed_error) : null;

  const delayMae = a.delay_mae_days != null ? Number(a.delay_mae_days) : null;
  const delayMse = a.delay_mean_error_days != null ? Number(a.delay_mean_error_days) : null;

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col justify-between">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-violet-500/15 border border-violet-400/30 text-violet-300">
            <Target className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Prediction Accuracy & Error Metrics
            </h3>
            <p className="text-xs text-slate-400">
              Mean absolute error (MAE), percentage error (MAPE), and directional bias
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-violet-300 bg-violet-500/10 px-2.5 py-1 rounded-lg border border-violet-500/20 self-start sm:self-auto">
          Statistical Benchmarking
        </div>
      </div>

      {/* Metrics Split Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
        {/* Cost Prediction Accuracy Card */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-white">
              <DollarSign className="h-3.5 w-3.5 text-red-400" />
              <span>Cost Prediction Accuracy</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {costEvaluated} records
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            {/* MAE */}
            <div className="p-2.5 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Mean Abs Error (MAE)</span>
              <span className="text-lg font-bold font-mono text-white mt-0.5 block">
                {costMae != null ? `$${costMae.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500">Average absolute dollar error</span>
            </div>

            {/* MAPE */}
            <div className="p-2.5 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">MAPE Error</span>
              <span className="text-lg font-bold font-mono text-red-400 mt-0.5 block">
                {costMape != null ? `${costMape.toFixed(1)}%` : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500">% of actual outcome cost</span>
            </div>

            {/* RMSE */}
            <div className="p-2.5 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">RMSE (Penalty)</span>
              <span className="text-base font-bold font-mono text-slate-200 mt-0.5 block">
                {costRmse != null ? `$${costRmse.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500">Penalizes large misses</span>
            </div>

            {/* Mean Signed Error (Bias) */}
            <div className="p-2.5 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Directional Bias</span>
              <span className={`text-base font-bold font-mono mt-0.5 block ${costMse != null && costMse > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {costMse != null ? `${costMse > 0 ? '+' : ''}$${costMse.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500">
                {costMse != null && costMse > 0 ? 'Under-predicted cost' : 'Conservative prediction'}
              </span>
            </div>
          </div>
        </div>

        {/* Delay Prediction Accuracy Card */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-white">
              <Clock className="h-3.5 w-3.5 text-amber-400" />
              <span>Delay Prediction Accuracy</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {delayEvaluated} records
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            {/* Delay MAE */}
            <div className="p-2.5 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Delay MAE</span>
              <span className="text-lg font-bold font-mono text-amber-400 mt-0.5 block">
                {delayMae != null ? `${delayMae.toFixed(2)} d` : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500">Average transit discrepancy</span>
            </div>

            {/* Delay Mean Signed Error */}
            <div className="p-2.5 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Delay Bias (Mean Signed)</span>
              <span className={`text-lg font-bold font-mono mt-0.5 block ${delayMse != null && delayMse > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {delayMse != null ? `${delayMse > 0 ? '+' : ''}${delayMse.toFixed(2)} d` : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500">
                {delayMse != null && delayMse > 0 ? 'Arrived later than forecast' : 'Arrived earlier/on-time'}
              </span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 text-[11px] text-slate-400 flex items-start space-x-2">
            <Info className="h-4 w-4 text-slate-500 flex-shrink-0 mt-0.5" />
            <p>
              Signed error measures structural model bias: positive delay bias indicates recommendations systemically underestimate lead times; positive cost bias indicates persistent cost overruns.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-white/[0.06] text-[11px] text-slate-500 flex items-center justify-between">
        <span>Evaluated against verified shipment receipts and delivery timestamps</span>
        <span className="font-mono text-slate-400">Currency: {currency}</span>
      </div>
    </div>
  );
}
