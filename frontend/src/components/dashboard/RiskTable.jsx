import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, ShieldAlert, ExternalLink } from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';

export default function RiskTable({
  shipments = [],
  loading = false,
  onSelectShipment,
}) {
  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl animate-pulse space-y-4">
        <div className="h-5 w-48 bg-white/10 rounded-md" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-white/5 rounded-xl w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (!shipments || shipments.length === 0) {
    return (
      <div className="glass-card p-8 rounded-2xl text-center flex flex-col items-center justify-center">
        <div className="p-3 rounded-full bg-emerald-500/10 text-emerald-400 mb-2 border border-emerald-500/20">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <h4 className="text-sm font-semibold text-slate-200">No High-Risk Shipments Flagged</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-sm">
          No stored predictions are currently classified in the critical high-risk tier (&ge; 70% delay probability).
        </p>
      </div>
    );
  }

  // Sort by delay probability descending
  const sortedShipments = [...shipments].sort(
    (a, b) => (Number(b.delay_probability) || 0) - (Number(a.delay_probability) || 0)
  );

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-rose-500/15 border border-rose-400/30 text-rose-300">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              High-Risk Shipment Alerts
            </h3>
            <p className="text-xs text-slate-400">
              Model-predicted delay likelihood requiring proactive intervention
            </p>
          </div>
        </div>

        <Link
          to="/shipments"
          className="text-xs font-semibold text-red-300 hover:text-red-200 flex items-center space-x-1 transition-colors"
        >
          <span>View all shipments</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono uppercase text-[11px]">
              <th className="py-3 px-4 font-semibold">Shipment ID</th>
              <th className="py-3 px-4 font-semibold">Supplier</th>
              <th className="py-3 px-4 font-semibold">Product</th>
              <th className="py-3 px-4 font-semibold">Delay Probability</th>
              <th className="py-3 px-4 font-semibold">Predicted Delay</th>
              <th className="py-3 px-4 font-semibold">Risk Level</th>
              <th className="py-3 px-4 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {sortedShipments.map((shipment) => {
              const prob = Number(shipment.delay_probability) || 0;
              const probPct = Math.round(prob * 100);
              const days = Number(shipment.predicted_delay_days) || 0;

              return (
                <tr
                  key={shipment.shipment_id}
                  className="hover:bg-white/[0.03] transition-colors"
                >
                  <td className="py-3.5 px-4 font-mono font-bold text-white">
                    {shipment.shipment_id}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">
                    {shipment.supplier_name || shipment.supplier_id || '—'}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">
                    {shipment.product_name || shipment.product_id || '—'}
                  </td>
                  <td className="py-3.5 px-4 font-mono">
                    <div className="flex items-center space-x-2">
                      <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-rose-500 rounded-full"
                          style={{ width: `${Math.min(100, probPct)}%` }}
                        />
                      </div>
                      <span className="text-rose-300 font-bold">{probPct}%</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-200">
                    +{days.toFixed(1)} days
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status="HIGH" variant="error" dot={true} />
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      to={`/shipments?search=${shipment.shipment_id}`}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-red-300 border border-white/[0.08] hover:border-red-500/30 transition-all"
                    >
                      <span>Details</span>
                      <ExternalLink className="h-3 w-3" />
                    </Link>
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
