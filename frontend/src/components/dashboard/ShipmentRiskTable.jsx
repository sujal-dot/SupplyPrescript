import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  AlertTriangle,
  Clock,
  Sparkles,
  CheckCircle2,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';
import GlassButton from '../ui/GlassButton';

export default function ShipmentRiskTable({
  shipments = [],
  selectedShipmentId = null,
  onSelectShipment,
  loading = false,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState('ALL'); // ALL, HIGH, MEDIUM, LOW

  const filteredShipments = useMemo(() => {
    if (!shipments) return [];
    return shipments.filter((s) => {
      // Risk filter
      const risk = (s.risk_level || (s.delay_probability >= 0.7 ? 'HIGH' : s.delay_probability >= 0.3 ? 'MEDIUM' : 'LOW')).toUpperCase();
      if (filterRisk !== 'ALL' && risk !== filterRisk) {
        return false;
      }

      // Search term
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const shipId = (s.shipment_id || '').toLowerCase();
        const supp = (s.supplier_name || s.supplier_id || '').toLowerCase();
        const prod = (s.product_name || s.product_id || '').toLowerCase();
        return shipId.includes(query) || supp.includes(query) || prod.includes(query);
      }
      return true;
    });
  }, [shipments, searchTerm, filterRisk]);

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] animate-pulse space-y-4">
        <div className="h-6 w-48 bg-white/10 rounded" />
        <div className="h-40 bg-white/5 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Header & Filter Controls */}
      <div className="p-5 border-b border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-bold text-white tracking-tight">
            Shipment Risk Monitor
          </h3>
          <p className="text-xs text-slate-400">
            Real-time transit portfolio; select any shipment to run prescriptive optimization
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Box */}
          <div className="relative">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search shipment, supplier..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-white/[0.04] border border-white/[0.08] focus:border-cyan-400/40 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none w-48 sm:w-56"
            />
          </div>

          {/* Risk Filter Buttons */}
          <div className="flex items-center space-x-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.06]">
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((risk) => (
              <button
                key={risk}
                onClick={() => setFilterRisk(risk)}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition-all ${
                  filterRisk === risk
                    ? 'bg-cyan-500/20 text-cyan-300 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {risk}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-96 overflow-y-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-[#0d1624] border-b border-white/[0.08] text-slate-400 font-mono uppercase text-[11px]">
            <tr>
              <th className="py-3 px-4 font-semibold">Shipment</th>
              <th className="py-3 px-4 font-semibold">Product</th>
              <th className="py-3 px-4 font-semibold">Supplier</th>
              <th className="py-3 px-4 font-semibold">Delay Probability</th>
              <th className="py-3 px-4 font-semibold">Predicted Delay</th>
              <th className="py-3 px-4 font-semibold">Risk Tier</th>
              <th className="py-3 px-4 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {filteredShipments.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                  No shipments found matching the specified filters.
                </td>
              </tr>
            ) : (
              filteredShipments.slice(0, 25).map((s) => {
                const isSelected = s.shipment_id === selectedShipmentId;
                const prob = Number(s.delay_probability) || 0;
                const probPct = Math.round(prob * 100);
                const delay = s.predicted_delay_days != null ? Number(s.predicted_delay_days) : (Number(s.delay_days) || 0);
                const risk = (s.risk_level || (prob >= 0.7 ? 'HIGH' : prob >= 0.3 ? 'MEDIUM' : 'LOW')).toUpperCase();

                return (
                  <tr
                    key={s.shipment_id}
                    className={`transition-colors ${
                      isSelected
                        ? 'bg-cyan-500/10 border-l-2 border-l-cyan-400'
                        : 'hover:bg-white/[0.02]'
                    }`}
                  >
                    <td className="py-3 px-4 font-mono font-bold text-white">
                      <div className="flex items-center space-x-1.5">
                        <span>{s.shipment_id}</span>
                        {isSelected && (
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-200">
                      {s.product_name || s.product_id || 'Industrial SKU'}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {s.supplier_name || s.supplier_id || '—'}
                    </td>
                    <td className="py-3 px-4 font-mono">
                      <div className="flex items-center space-x-2">
                        <div className="w-12 h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              probPct >= 70
                                ? 'bg-rose-500'
                                : probPct >= 30
                                ? 'bg-amber-400'
                                : 'bg-emerald-400'
                            }`}
                            style={{ width: `${Math.min(100, probPct)}%` }}
                          />
                        </div>
                        <span className="text-slate-300 font-semibold">{probPct}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono">
                      <span className={delay > 0 ? 'text-rose-400 font-semibold' : 'text-slate-400'}>
                        +{delay.toFixed(1)} d
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge
                        status={risk}
                        variant={risk === 'HIGH' ? 'error' : risk === 'MEDIUM' ? 'warning' : 'success'}
                      />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onSelectShipment?.(s)}
                        className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                          isSelected
                            ? 'bg-cyan-500 text-white shadow-md shadow-cyan-500/30'
                            : 'bg-white/[0.04] hover:bg-cyan-500/20 text-cyan-300 border border-white/[0.08] hover:border-cyan-400/30'
                        }`}
                      >
                        <Sparkles className="h-3 w-3" />
                        <span>{isSelected ? 'Optimized' : 'Optimize'}</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
