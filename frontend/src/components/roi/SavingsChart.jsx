import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { TrendingUp, AlertCircle, Info, ShieldCheck } from 'lucide-react';

export default function SavingsChart({
  timeline = [],
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

  const items = Array.isArray(timeline) ? timeline : [];

  if (items.length === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col items-center justify-center text-center text-slate-400" style={{ height }}>
        <AlertCircle className="h-8 w-8 text-slate-500 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Savings Timeline Data</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No sequential decisions with completed financial comparisons found in the selected date range.
        </p>
      </div>
    );
  }

  // Last point represents cumulative totals to date
  const latest = items[items.length - 1] || {};
  const totalForecastVariance = latest.cumulative_forecast_variance ?? 0;
  const totalBaselineSavings = latest.cumulative_baseline_savings ?? 0;

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col justify-between">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/15 border border-emerald-400/30 text-emerald-300">
            <TrendingUp className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Cumulative Savings & Variance Analysis
            </h3>
            <p className="text-xs text-slate-400">
              Comparing forecast variance vs verified causal baseline savings over time
            </p>
          </div>
        </div>

        {/* Top Cumulative Metrics */}
        <div className="flex items-center space-x-3 text-xs self-start sm:self-auto font-mono">
          <div className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <span className="text-[10px] text-slate-400 block font-sans">Verified Baseline Savings:</span>
            <span className="font-bold">${totalBaselineSavings.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          <div className="px-2.5 py-1 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
            <span className="text-[10px] text-slate-400 block font-sans">Forecast Variance:</span>
            <span className="font-bold">${totalForecastVariance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full flex-1" style={{ minHeight: height - 100 }}>
        <ResponsiveContainer width="100%" height={height - 100}>
          <AreaChart data={items} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="baselineSavingsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="forecastVarianceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#EF4444" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" vertical={false} />
            <XAxis
              dataKey="date"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
            />
            <YAxis
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              tickFormatter={(v) => `$${v.toLocaleString()}`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="glass-card p-3 rounded-xl border border-white/20 shadow-xl text-xs space-y-1.5 backdrop-blur-md">
                      <div className="font-semibold text-white border-b border-white/10 pb-1 flex justify-between gap-4">
                        <span>Period: {label}</span>
                        <span className="font-mono text-slate-400">{d.decision_count} decisions</span>
                      </div>
                      <div className="space-y-1 pt-1">
                        <div className="flex justify-between items-center text-emerald-400">
                          <span>Verified Baseline Savings:</span>
                          <span className="font-mono font-bold">${d.cumulative_baseline_savings?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div className="flex justify-between items-center text-red-400">
                          <span>Forecast Variance (Cumul):</span>
                          <span className="font-mono font-bold">${d.cumulative_forecast_variance?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
              iconType="circle"
            />
            <Area
              type="monotone"
              dataKey="cumulative_baseline_savings"
              name="Verified Baseline Savings (Baseline - Actual)"
              stroke="#10B981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#baselineSavingsGrad)"
            />
            <Area
              type="monotone"
              dataKey="cumulative_forecast_variance"
              name="Forecast Variance (Predicted - Actual)"
              stroke="#EF4444"
              strokeWidth={2}
              strokeDasharray="4 4"
              fillOpacity={1}
              fill="url(#forecastVarianceGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Critical Methodology Callout */}
      <div className="mt-3 pt-2.5 border-t border-white/[0.06] text-[11px] text-slate-400 flex items-start space-x-2">
        <Info className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
        <p>
          <strong className="text-slate-300">Methodological Separation:</strong> Forecast variance (predicted − actual) measures whether operational execution beat the ML forecast. Verified baseline savings (baseline − actual) measures dollars saved compared to the unmitigated shipment baseline.
        </p>
      </div>
    </div>
  );
}
