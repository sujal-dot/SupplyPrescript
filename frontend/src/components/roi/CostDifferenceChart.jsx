import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from 'recharts';
import { Scale, AlertCircle, Info } from 'lucide-react';

export default function CostDifferenceChart({
  strategyCostDifferences = [],
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

  const items = Array.isArray(strategyCostDifferences) ? strategyCostDifferences : [];
  const validItems = items.filter((d) => d.average_cost_difference != null && d.count > 0);

  if (validItems.length === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col items-center justify-center text-center text-slate-400" style={{ height }}>
        <AlertCircle className="h-8 w-8 text-slate-500 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Cost Variance Data</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No decisions with completed actual and predicted costs in {currency} are available for strategy comparison.
        </p>
      </div>
    );
  }

  const chartData = validItems.map((d) => {
    const avgDiff = Number(d.average_cost_difference);
    const label = d.strategy ? d.strategy.replace(/_/g, ' ') : 'Unspecified';
    return {
      strategy: label,
      rawStrategy: d.strategy,
      avgDiff,
      count: d.count,
      predCost: d.total_predicted_cost ? Number(d.total_predicted_cost) : 0,
      actCost: d.total_actual_cost ? Number(d.total_actual_cost) : 0,
      isUnderBudget: avgDiff <= 0,
    };
  });

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col justify-between">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-rose-500/15 border border-rose-400/30 text-rose-300">
            <Scale className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Average Cost Difference by Strategy
            </h3>
            <p className="text-xs text-slate-400">
              actual_cost - predicted_cost (negative = under budget, positive = overrun)
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-400 bg-white/[0.04] px-2.5 py-1 rounded-lg border border-white/[0.06] self-start sm:self-auto">
          Currency: {currency}
        </div>
      </div>

      {/* Bar Chart */}
      <div className="w-full flex-1" style={{ minHeight: height - 80 }}>
        <ResponsiveContainer width="100%" height={height - 80}>
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
              tickFormatter={(v) => `${v > 0 ? '+' : ''}$${v.toLocaleString()}`}
            />
            <ReferenceLine y={0} stroke="rgba(255, 255, 255, 0.25)" strokeDasharray="2 2" />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  const isNegative = d.avgDiff < 0;
                  return (
                    <div className="glass-card p-3 rounded-xl border border-white/20 shadow-xl text-xs space-y-1.5 backdrop-blur-md">
                      <div className="font-semibold text-white border-b border-white/10 pb-1 flex justify-between gap-4">
                        <span>{d.strategy}</span>
                        <span className="font-mono text-slate-400">({d.count} decisions)</span>
                      </div>
                      <div className="flex justify-between items-center text-[11px] pt-1">
                        <span className="text-slate-400">Avg Cost Difference:</span>
                        <span className={`font-mono font-bold ${isNegative ? 'text-emerald-400' : d.avgDiff === 0 ? 'text-slate-300' : 'text-rose-400'}`}>
                          {d.avgDiff > 0 ? '+' : ''}${d.avgDiff.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {currency}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 pt-1 border-t border-white/5">
                        {isNegative ? 'Actuals performed better than forecast' : 'Actuals experienced cost overruns'}
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="avgDiff" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`bar-${index}`}
                  fill={entry.avgDiff < 0 ? '#10B981' : entry.avgDiff === 0 ? '#64748B' : '#EF4444'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Interpretation Footer */}
      <div className="mt-2 pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400">
        <span className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded bg-emerald-500 inline-block" />
          <span>Negative: Under Budget / Savings vs Forecast</span>
        </span>
        <span className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded bg-rose-500 inline-block" />
          <span>Positive: Cost Overrun</span>
        </span>
      </div>
    </div>
  );
}
