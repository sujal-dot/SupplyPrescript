import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { TrendingUp, AlertCircle } from 'lucide-react';

export default function DelayTrendChart({
  data = [],
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

  if (!data || data.length === 0) {
    return (
      <div className="glass-card p-8 rounded-2xl flex flex-col items-center justify-center text-center text-slate-400" style={{ height }}>
        <AlertCircle className="h-8 w-8 text-slate-500 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Delay Trends Available</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-sm">
          No historical shipment delay records found for time-series grouping.
        </p>
      </div>
    );
  }

  // Format month labels nicely (e.g. '2023-01' -> 'Jan 23')
  const chartData = data.map((d) => {
    let formattedLabel = d.month || d.label || '';
    if (formattedLabel && formattedLabel.includes('-')) {
      const parts = formattedLabel.split('-');
      if (parts.length === 2) {
        const year = parts[0].slice(2);
        const monthNum = parseInt(parts[1], 10);
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        formattedLabel = `${monthNames[monthNum - 1] || parts[1]} '${year}`;
      }
    }
    return {
      period: formattedLabel,
      avgDelay: Number(d.average_delay_days || 0),
      delayedCount: Number(d.delayed_shipments || 0),
      totalCount: Number(d.total_shipments || 0),
    };
  });

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
            <TrendingUp className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Historical Delay Trends Over Time
            </h3>
            <p className="text-xs text-slate-400">
              Aggregated monthly shipment outcomes from database
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-400 bg-white/[0.04] px-2.5 py-1 rounded-lg border border-white/[0.06] self-start sm:self-auto">
          Actual Historical Delivery Outcomes
        </div>
      </div>

      <div className="w-full flex-1" style={{ minHeight: height }}>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="redLineGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#EF4444" />
                <stop offset="100%" stopColor="#F43F5E" />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" vertical={false} />
            <XAxis
              dataKey="period"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
            />
            <YAxis
              yAxisId="left"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
              unit=" d"
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="glass-card p-3 rounded-xl border border-white/20 shadow-xl text-xs space-y-1.5 backdrop-blur-md">
                      <div className="font-semibold text-white border-b border-white/10 pb-1">
                        {label}
                      </div>
                      <div className="flex items-center justify-between space-x-3 text-red-300">
                        <span>Avg Delay:</span>
                        <span className="font-mono font-bold">{payload[0]?.value} days</span>
                      </div>
                      {payload[1] && (
                        <div className="flex items-center justify-between space-x-3 text-amber-300">
                          <span>Delayed Shipments:</span>
                          <span className="font-mono font-bold">{payload[1]?.value}</span>
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend
              wrapperStyle={{ paddingTop: '12px', fontSize: '11px' }}
              formatter={(value) => <span className="text-slate-300">{value}</span>}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="avgDelay"
              name="Avg Delay Days"
              stroke="#EF4444"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#EF4444', stroke: '#0C0406', strokeWidth: 1.5 }}
              activeDot={{ r: 5, fill: '#ffffff', stroke: '#EF4444', strokeWidth: 2 }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="delayedCount"
              name="Delayed Shipments Count"
              stroke="#F59E0B"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
