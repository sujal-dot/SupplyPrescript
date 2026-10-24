import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
} from 'recharts';
import { Layers, AlertCircle, TrendingUp, HelpCircle } from 'lucide-react';

export default function ROIByStrategyChart({
  strategyROI = [],
  currency = 'USD',
  loading = false,
  height = 300,
}) {
  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl animate-pulse flex flex-col justify-between" style={{ height }}>
        <div className="h-5 w-48 bg-white/10 rounded-md" />
        <div className="h-44 w-full bg-white/5 rounded-xl" />
        <div className="h-4 w-32 bg-white/10 rounded-md" />
      </div>
    );
  }

  const items = Array.isArray(strategyROI) ? strategyROI : [];

  if (items.length === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col items-center justify-center text-center text-slate-400" style={{ height }}>
        <AlertCircle className="h-8 w-8 text-slate-500 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Strategy ROI Data</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No strategy records available to calculate ROI. Execute recommendations to compare strategy performance.
        </p>
      </div>
    );
  }

  const chartData = items.map((item) => {
    const label = item.strategy ? item.strategy.replace(/_/g, ' ') : 'Unspecified';
    const hasRoi = item.roi_status === 'CALCULATED' && item.roi_percentage != null;
    return {
      strategy: label,
      rawStrategy: item.strategy,
      roiPercentage: hasRoi ? Number(item.roi_percentage) : 0,
      hasRoi,
      roiStatus: item.roi_status,
      roiReason: item.roi_reason,
      totalDecisions: item.total_decisions,
      completedDecisions: item.completed_decisions,
      successRate: item.success_rate != null ? Number(item.success_rate) : null,
      baselineSavings: item.verified_baseline_savings,
      investmentCost: item.total_investment_cost,
      netBenefit: item.total_net_benefit,
    };
  });

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col justify-between">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-violet-500/15 border border-violet-400/30 text-violet-300">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Return on Investment (ROI) by Strategy
            </h3>
            <p className="text-xs text-slate-400">
              (Net Benefit / Incremental Investment) × 100 for documented capital outlays
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-violet-300 bg-violet-500/10 px-2.5 py-1 rounded-lg border border-violet-500/20 self-start sm:self-auto">
          Weighted Strategy Aggregate
        </div>
      </div>

      {/* Bar Chart & Cards for Unavailable Denominators */}
      <div className="w-full flex-1" style={{ minHeight: height - 100 }}>
        <ResponsiveContainer width="100%" height={height - 100}>
          <BarChart data={chartData} margin={{ top: 15, right: 20, left: 0, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" vertical={false} />
            <XAxis
              dataKey="strategy"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              interval={0}
              angle={-15}
              textAnchor="end"
            />
            <YAxis
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <ReferenceLine y={0} stroke="rgba(255, 255, 255, 0.25)" strokeDasharray="2 2" />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="glass-card p-3 rounded-xl border border-white/20 shadow-xl text-xs space-y-1.5 backdrop-blur-md max-w-xs">
                      <div className="font-semibold text-white border-b border-white/10 pb-1 flex justify-between gap-4">
                        <span>{d.strategy}</span>
                        <span className="font-mono text-slate-400">({d.totalDecisions} decisions)</span>
                      </div>
                      <div className="space-y-1 pt-1 text-[11px]">
                        <div className="flex justify-between items-center">
                          <span className="text-slate-400">ROI %:</span>
                          <span className={`font-mono font-bold ${d.hasRoi ? 'text-emerald-400' : 'text-slate-400'}`}>
                            {d.hasRoi ? `${d.roiPercentage > 0 ? '+' : ''}${d.roiPercentage.toFixed(1)}%` : 'N/A (Denominator Pending)'}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-400">Success Rate:</span>
                          <span className="font-mono text-red-400">
                            {d.successRate != null ? `${d.successRate.toFixed(1)}%` : 'N/A'}
                          </span>
                        </div>
                        {d.baselineSavings != null ? (
                          <div className="flex justify-between items-center">
                            <span className="text-slate-400">Baseline Savings:</span>
                            <span className="font-mono text-emerald-400 font-bold">${Number(d.baselineSavings).toLocaleString()}</span>
                          </div>
                        ) : null}
                      </div>
                      <div className="text-[10px] text-slate-400 pt-1 border-t border-white/5">
                        {d.roiReason}
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="roiPercentage" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`roi-cell-${index}`}
                  fill={!entry.hasRoi ? '#334155' : entry.roiPercentage >= 0 ? '#10B981' : '#EF4444'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Transparent Strategy Summary Row */}
      <div className="mt-3 pt-2.5 border-t border-white/[0.06] grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
        {items.map((it) => (
          <div key={it.strategy} className="p-2 rounded-lg bg-white/[0.02] border border-white/5">
            <div className="font-medium text-slate-300 truncate">{it.strategy.replace(/_/g, ' ')}</div>
            <div className="flex justify-between items-center mt-1">
              <span className="text-slate-500">ROI:</span>
              <span className={`font-mono font-bold ${it.roi_status === 'CALCULATED' ? 'text-emerald-400' : 'text-slate-400'}`}>
                {it.roi_status === 'CALCULATED' && it.roi_percentage != null ? `${it.roi_percentage > 0 ? '+' : ''}${it.roi_percentage.toFixed(1)}%` : 'N/A'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
