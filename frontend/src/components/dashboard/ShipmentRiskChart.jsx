import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts';
import { ShieldAlert, AlertCircle } from 'lucide-react';

export default function ShipmentRiskChart({
  distribution = null, // { LOW: 14, MEDIUM: 9, HIGH: 4 }
  loading = false,
  height = 300,
}) {
  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl animate-pulse flex flex-col justify-between" style={{ height }}>
        <div className="h-5 w-48 bg-white/10 rounded-md" />
        <div className="h-44 w-full bg-white/5 rounded-full mx-auto" />
        <div className="h-4 w-32 bg-white/10 rounded-md mx-auto" />
      </div>
    );
  }

  const lowCount = distribution?.LOW || 0;
  const medCount = distribution?.MEDIUM || 0;
  const highCount = distribution?.HIGH || 0;
  const total = lowCount + medCount + highCount;

  if (!distribution || total === 0) {
    return (
      <div className="glass-card p-8 rounded-2xl flex flex-col items-center justify-center text-center text-slate-400" style={{ height }}>
        <AlertCircle className="h-8 w-8 text-slate-500 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">No Prediction Records Available</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No stored shipment predictions found in the database. Run predictions from the Predictions page to view risk distributions.
        </p>
      </div>
    );
  }

  const chartData = [
    { name: 'Low Risk (<30%)', key: 'LOW', value: lowCount, color: '#34D399' },
    { name: 'Medium Risk (30-69%)', key: 'MEDIUM', value: medCount, color: '#FBBF24' },
    { name: 'High Risk (≥70%)', key: 'HIGH', value: highCount, color: '#FB7185' },
  ].filter((item) => item.value > 0);

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-rose-500/15 border border-rose-400/30 text-rose-300">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Shipment Delay Risk Distribution
            </h3>
            <p className="text-xs text-slate-400">
              Active XGBoost classification tiers on stored records
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-400 bg-white/[0.04] px-2.5 py-1 rounded-lg border border-white/[0.06] self-start sm:self-auto">
          {total} Active Predictions
        </div>
      </div>

      <div className="w-full flex-1 relative flex items-center justify-center" style={{ minHeight: height }}>
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload;
                  const pct = Math.round((item.value / total) * 100);
                  return (
                    <div className="glass-card p-3 rounded-xl border border-white/20 shadow-xl text-xs space-y-1 backdrop-blur-md">
                      <div className="font-semibold text-white flex items-center space-x-2">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                        <span>{item.name}</span>
                      </div>
                      <div className="flex items-center justify-between space-x-4 text-slate-300 pt-1 border-t border-white/10">
                        <span>Predicted Shipments:</span>
                        <span className="font-mono font-bold text-white">
                          {item.value} ({pct}%)
                        </span>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              formatter={(value, entry) => (
                <span className="text-slate-300 text-xs">
                  {value} ({entry.payload.value})
                </span>
              )}
            />
            <Pie
              data={chartData}
              cx="50%"
              cy="45%"
              innerRadius={65}
              outerRadius={95}
              paddingAngle={4}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="#07111F" strokeWidth={2} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute top-[40%] left-1/2 -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none">
          <div className="text-2xl font-black font-mono text-white">{total}</div>
          <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
            Evaluated
          </div>
        </div>
      </div>
    </div>
  );
}
