import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';
import { ShieldCheck, AlertCircle, Info } from 'lucide-react';

export default function DecisionSuccessChart({
  breakdown = [],
  summary = {},
  loading = false,
  height = 300,
}) {
  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl animate-pulse flex flex-col justify-between" style={{ height }}>
        <div className="h-5 w-48 bg-white/10 rounded-md" />
        <div className="h-44 w-44 rounded-full bg-white/5 mx-auto" />
        <div className="h-4 w-32 bg-white/10 rounded-md mx-auto" />
      </div>
    );
  }

  const items = Array.isArray(breakdown) ? breakdown : [];
  const total = items.reduce((acc, curr) => acc + (curr.count || 0), 0);
  const eligible = (summary.eligible_completed_decisions ?? 0);
  const successRate = summary.success_rate != null ? Number(summary.success_rate) : null;

  if (total === 0) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col items-center justify-center text-center text-slate-400" style={{ height }}>
        <AlertCircle className="h-8 w-8 text-slate-500 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Decision Outcomes Found</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No decisions match the current filter selection. Adjust filters or execute recommendations to evaluate decision success.
        </p>
      </div>
    );
  }

  const chartData = items.map((item) => ({
    name: item.label,
    key: item.status,
    value: item.count,
    color: item.color,
    pctEligible: item.percentage_of_eligible,
    pctTotal: item.percentage_of_total,
    description: item.description,
  })).filter((d) => d.value > 0);

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col justify-between">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/15 border border-emerald-400/30 text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Recommendation Success vs Failure
            </h3>
            <p className="text-xs text-slate-400">
              Closed-loop multi-dimensional evaluation of persisted operational outcomes
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20 self-start sm:self-auto">
          {successRate != null ? `${successRate.toFixed(1)}% Success Rate` : 'Evaluating Actuals'}
        </div>
      </div>

      {/* Donut Chart with Centered Rate */}
      <div className="relative w-full flex-1 flex items-center justify-center" style={{ minHeight: height - 100 }}>
        <ResponsiveContainer width="100%" height={height - 100}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              paddingAngle={3}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="#0C0406" strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="glass-card p-3 rounded-xl border border-white/20 shadow-xl text-xs space-y-1.5 backdrop-blur-md max-w-xs">
                      <div className="font-semibold text-white flex items-center justify-between border-b border-white/10 pb-1">
                        <span className="flex items-center space-x-1.5">
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: data.color }} />
                          <span>{data.name}</span>
                        </span>
                        <span className="font-mono text-slate-300">{data.value} decisions</span>
                      </div>
                      <div className="text-slate-300 text-[11px]">
                        {data.pctEligible != null ? (
                          <div>
                            <span className="text-slate-400">Rate (of completed): </span>
                            <span className="font-bold font-mono text-white">{data.pctEligible.toFixed(1)}%</span>
                          </div>
                        ) : null}
                        <div>
                          <span className="text-slate-400">Share of Total: </span>
                          <span className="font-mono">{data.pctTotal?.toFixed(1)}%</span>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-400 pt-1 border-t border-white/5">
                        {data.description}
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Center Donut Label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-xl font-bold font-mono text-white">
            {eligible > 0 ? `${successRate?.toFixed(0) || 0}%` : `${total}`}
          </span>
          <span className="text-[10px] text-slate-400 font-medium">
            {eligible > 0 ? 'Success' : 'Decisions'}
          </span>
        </div>
      </div>

      {/* Legend & Denominator Transparency */}
      <div className="mt-4 pt-3 border-t border-white/[0.06] space-y-2">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          {items.map((cat) => (
            <div key={cat.status} className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
              <div className="truncate">
                <span className="text-slate-300 font-medium">{cat.label}: </span>
                <span className="font-mono text-white font-bold">{cat.count}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 pt-1">
          <Info className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
          <span>
            Success rate denominator = {eligible} completed decisions (excludes {summary.pending_decisions ?? 0} pending review).
          </span>
        </div>
      </div>
    </div>
  );
}
