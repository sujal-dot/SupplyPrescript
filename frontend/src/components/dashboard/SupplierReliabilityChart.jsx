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
} from 'recharts';
import { Award, AlertCircle } from 'lucide-react';

export default function SupplierReliabilityChart({
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
        <h4 className="text-sm font-semibold text-slate-300">No Supplier Records</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-sm">
          No supplier reliability metrics are currently stored in the database.
        </p>
      </div>
    );
  }

  // Format data: ensure percentage formatting (e.g. 0.95 -> 95%)
  const chartData = data.slice(0, 8).map((d) => {
    let rawRel = d.reliability !== undefined ? d.reliability : d.supplier_reliability;
    let pct = rawRel !== undefined && rawRel !== null ? Number(rawRel) : 0;
    if (pct <= 1.0) {
      pct = Math.round(pct * 1000) / 10; // e.g. 0.985 -> 98.5
    } else {
      pct = Math.round(pct * 10) / 10;
    }

    return {
      name: d.supplier_name || d.supplier_id || 'Unknown',
      id: d.supplier_id || '',
      reliabilityPct: pct,
      shipmentCount: d.shipment_count || 0,
    };
  });

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/[0.08] flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/15 border border-emerald-400/30 text-emerald-300">
            <Award className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Top Suppliers by Reliability
            </h3>
            <p className="text-xs text-slate-400">
              Contracted reliability score & total fulfilled shipments
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-emerald-300 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-400/20 self-start sm:self-auto">
          Operational Benchmarks
        </div>
      </div>

      <div className="w-full flex-1" style={{ minHeight: height }}>
        <ResponsiveContainer width="100%" height={height}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" horizontal={false} />
            <XAxis
              type="number"
              domain={[60, 100]}
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              unit="%"
            />
            <YAxis
              type="category"
              dataKey="name"
              stroke="#CBD5E1"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={110}
              tickFormatter={(val) => (val.length > 14 ? `${val.slice(0, 14)}…` : val)}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload;
                  return (
                    <div className="glass-card p-3 rounded-xl border border-white/20 shadow-xl text-xs space-y-1 backdrop-blur-md">
                      <div className="font-semibold text-white border-b border-white/10 pb-1">
                        {item.name} <span className="text-slate-400 font-mono">({item.id})</span>
                      </div>
                      <div className="flex items-center justify-between space-x-3 text-emerald-300">
                        <span>Reliability Score:</span>
                        <span className="font-mono font-bold">{item.reliabilityPct}%</span>
                      </div>
                      <div className="flex items-center justify-between space-x-3 text-slate-300">
                        <span>Sample Size:</span>
                        <span className="font-mono font-semibold">{item.shipmentCount} shipments</span>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="reliabilityPct" radius={[0, 6, 6, 0]} barSize={16}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    entry.reliabilityPct >= 95
                      ? '#34D399'
                      : entry.reliabilityPct >= 85
                      ? '#22D3EE'
                      : '#F59E0B'
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
