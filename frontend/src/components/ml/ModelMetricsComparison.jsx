import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  Sliders,
  HelpCircle,
  Cpu,
  Target,
} from 'lucide-react';

export default function ModelMetricsComparison({
  baselineMetrics = {},
  candidateMetrics = {},
  baselineVersion = 'v1.0',
  candidateVersion = 'v1.1',
}) {
  const baseReg = baselineMetrics.regression || {};
  const candReg = candidateMetrics.regression || {};
  const baseCls = baselineMetrics.classification || {};
  const candCls = candidateMetrics.classification || {};

  const metricsList = [
    {
      name: 'Delay MAE (Mean Absolute Error)',
      base: baseReg.mae != null ? `${Number(baseReg.mae).toFixed(3)} d` : '—',
      cand: candReg.mae != null ? `${Number(candReg.mae).toFixed(3)} d` : '—',
      improvement:
        baseReg.mae && candReg.mae
          ? ((baseReg.mae - candReg.mae) / baseReg.mae) * 100
          : null,
      isLowerBetter: true,
    },
    {
      name: 'RMSE (Root Mean Squared Error)',
      base: baseReg.rmse != null ? `${Number(baseReg.rmse).toFixed(3)} d` : '—',
      cand: candReg.rmse != null ? `${Number(candReg.rmse).toFixed(3)} d` : '—',
      improvement:
        baseReg.rmse && candReg.rmse
          ? ((baseReg.rmse - candReg.rmse) / baseReg.rmse) * 100
          : null,
      isLowerBetter: true,
    },
    {
      name: 'Median Absolute Error',
      base:
        baseReg.median_absolute_error != null
          ? `${Number(baseReg.median_absolute_error).toFixed(3)} d`
          : '—',
      cand:
        candReg.median_absolute_error != null
          ? `${Number(candReg.median_absolute_error).toFixed(3)} d`
          : '—',
      improvement:
        baseReg.median_absolute_error && candReg.median_absolute_error
          ? ((baseReg.median_absolute_error - candReg.median_absolute_error) /
              baseReg.median_absolute_error) *
            100
          : null,
      isLowerBetter: true,
    },
    {
      name: 'Classifier F1-Score',
      base: baseCls.f1_score != null ? Number(baseCls.f1_score).toFixed(3) : '—',
      cand: candCls.f1_score != null ? Number(candCls.f1_score).toFixed(3) : '—',
      improvement:
        baseCls.f1_score && candCls.f1_score
          ? ((candCls.f1_score - baseCls.f1_score) / baseCls.f1_score) * 100
          : null,
      isLowerBetter: false,
    },
    {
      name: 'Classifier ROC-AUC',
      base: baseCls.roc_auc != null ? Number(baseCls.roc_auc).toFixed(3) : '—',
      cand: candCls.roc_auc != null ? Number(candCls.roc_auc).toFixed(3) : '—',
      improvement:
        baseCls.roc_auc && candCls.roc_auc
          ? ((candCls.roc_auc - baseCls.roc_auc) / baseCls.roc_auc) * 100
          : null,
      isLowerBetter: false,
    },
  ];

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden mb-6">
      <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-violet-500/15 border border-violet-400/30 text-violet-300">
            <Sliders className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Baseline vs Candidate Metrics Comparison
            </h3>
            <p className="text-xs text-slate-400">
              Direct statistical benchmarking across dual regression and classification engines
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-white/[0.08] bg-white/[0.02] text-slate-400 font-medium">
              <th className="py-3 px-4">Evaluation Metric</th>
              <th className="py-3 px-4 font-mono text-slate-300">
                Baseline ({baselineVersion})
              </th>
              <th className="py-3 px-4 font-mono text-red-300">
                Candidate ({candidateVersion})
              </th>
              <th className="py-3 px-4 text-right">Comparative Delta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {metricsList.map((m) => {
              const hasDelta = m.improvement != null;
              const isPositive = m.isLowerBetter ? m.improvement >= 0 : m.improvement >= 0;

              return (
                <tr key={m.name} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 px-4 font-medium text-slate-200">{m.name}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{m.base}</td>
                  <td className="py-3 px-4 font-mono font-semibold text-white">{m.cand}</td>
                  <td className="py-3 px-4 text-right font-mono">
                    {hasDelta ? (
                      <span
                        className={`inline-flex items-center space-x-1 font-semibold ${
                          isPositive ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {isPositive ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : (
                          <TrendingDown className="h-3 w-3" />
                        )}
                        <span>
                          {m.improvement > 0 ? `+${m.improvement.toFixed(1)}%` : `${m.improvement.toFixed(1)}%`}
                        </span>
                      </span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
