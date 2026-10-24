import React, { useState } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Sparkles,
  AlertCircle,
  Truck,
  ArrowUpDown,
} from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';
import GlassButton from '../ui/GlassButton';

export default function ShipmentTable({
  shipments = [],
  total = 0,
  page = 1,
  pageSize = 20,
  totalPages = 1,
  loading = false,
  onPageChange,
  onSearchChange,
  onFilterChange,
  onSortChange,
  onRefresh,
  onSelectShipment,
  filters = {},
}) {
  const [searchTerm, setSearchTerm] = useState(filters.search || '');

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (onSearchChange) onSearchChange(searchTerm);
  };

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Header Controls */}
      <div className="p-4 sm:p-5 border-b border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onBlur={() => onSearchChange && onSearchChange(searchTerm)}
            placeholder="Search shipment ID (e.g. SHIP000100)..."
            className="w-full glass-input text-xs pl-10 pr-4 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-red-500"
          />
        </form>

        {/* Filters and Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Transport mode filter */}
          <select
            value={filters.transport_mode || ''}
            onChange={(e) => onFilterChange && onFilterChange('transport_mode', e.target.value)}
            className="glass-input text-xs px-3 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-slate-300 focus:outline-none focus:border-red-500"
          >
            <option value="">All Modes</option>
            <option value="Road">Road</option>
            <option value="Rail">Rail</option>
            <option value="Air">Air</option>
            <option value="Sea">Sea</option>
          </select>

          {/* Delay Status filter */}
          <select
            value={filters.is_delayed !== undefined ? String(filters.is_delayed) : ''}
            onChange={(e) => {
              const val = e.target.value;
              onFilterChange && onFilterChange('is_delayed', val === '' ? null : val === 'true');
            }}
            className="glass-input text-xs px-3 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-slate-300 focus:outline-none focus:border-red-500"
          >
            <option value="">All Delivery Statuses</option>
            <option value="false">On-Time Only</option>
            <option value="true">Delayed Only</option>
          </select>

          {/* Sort By */}
          <select
            value={filters.sort_by || 'order_date'}
            onChange={(e) => onSortChange && onSortChange(e.target.value)}
            className="glass-input text-xs px-3 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-slate-300 focus:outline-none focus:border-red-500"
          >
            <option value="order_date">Sort: Order Date</option>
            <option value="quantity">Sort: Quantity</option>
            <option value="shipping_cost">Sort: Shipping Cost</option>
            <option value="delay_days">Sort: Actual Delay Days</option>
            <option value="lead_time">Sort: Lead Time</option>
          </select>

          {/* Refresh Button */}
          {onRefresh && (
            <GlassButton
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              loading={loading}
              onClick={onRefresh}
            >
              Refresh
            </GlassButton>
          )}
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto min-h-[300px]">
        {loading ? (
          <div className="p-8 space-y-4 animate-pulse">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-10 bg-white/5 rounded-xl w-full" />
            ))}
          </div>
        ) : shipments.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center text-slate-400">
            <Truck className="h-10 w-10 text-slate-500 mb-2" />
            <h4 className="text-sm font-semibold text-slate-300">No Shipments Found</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              No shipment records matched your search or active filter criteria. Try clearing filters or searching for another ID.
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono uppercase text-[11px]">
                <th className="py-3 px-4 font-semibold">Shipment ID</th>
                <th className="py-3 px-4 font-semibold">Supplier</th>
                <th className="py-3 px-4 font-semibold">Product</th>
                <th className="py-3 px-4 font-semibold">Quantity</th>
                <th className="py-3 px-4 font-semibold">Transit</th>
                <th className="py-3 px-4 font-semibold">Expected Delivery</th>
                <th className="py-3 px-4 font-semibold">Actual Outcome</th>
                <th className="py-3 px-4 font-semibold">Predicted Delay</th>
                <th className="py-3 px-4 font-semibold">Predicted Risk</th>
                <th className="py-3 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {shipments.map((s) => {
                const isDelayed = s.delay_days > 0;
                const hasPrediction =
                  s.prediction_probability !== null &&
                  s.prediction_probability !== undefined;
                const probPct = hasPrediction
                  ? Math.round(Number(s.prediction_probability) * 100)
                  : null;
                const riskLevel = s.risk_level || 'Not predicted';

                return (
                  <tr
                    key={s.shipment_id}
                    className="hover:bg-white/[0.03] transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-white">
                      {s.shipment_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {s.supplier_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {s.product_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-200">
                      {Number(s.quantity).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-mono bg-white/[0.04] text-slate-300 border border-white/[0.06]">
                        {s.transport_mode}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 font-mono">
                      {s.expected_delivery_date || '—'}
                    </td>
                    <td className="py-3.5 px-4">
                      {isDelayed ? (
                        <StatusBadge
                          status={`Delayed (+${s.delay_days}d)`}
                          variant="error"
                          dot={true}
                        />
                      ) : (
                        <StatusBadge status="On-Time" variant="success" dot={true} />
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      {hasPrediction ? (
                        <div className="flex items-center space-x-1.5">
                          <span
                            className={
                              probPct >= 70
                                ? 'text-rose-400 font-bold'
                                : probPct >= 30
                                ? 'text-amber-400 font-semibold'
                                : 'text-emerald-400'
                            }
                          >
                            {probPct}%
                          </span>
                          <span className="text-slate-400 text-[10px]">
                            (+{Number(s.predicted_delay_days || 0).toFixed(1)}d)
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">Not predicted</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      {hasPrediction ? (
                        <StatusBadge
                          status={riskLevel}
                          variant={
                            riskLevel === 'HIGH'
                              ? 'error'
                              : riskLevel === 'MEDIUM'
                              ? 'warning'
                              : 'success'
                          }
                          dot={true}
                        />
                      ) : (
                        <span className="text-slate-500 text-[11px]">Pending ML</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {onSelectShipment && (
                        <button
                          onClick={() => onSelectShipment(s)}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-red-300 border border-white/[0.08] hover:border-red-500/30 transition-all"
                        >
                          <span>Inspect</span>
                          <ExternalLink className="h-3 w-3" />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Controls */}
      <div className="p-4 border-t border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="text-slate-400 font-mono">
          Showing page <span className="text-white font-bold">{page}</span> of{' '}
          <span className="text-white font-bold">{totalPages || 1}</span> ({total.toLocaleString()} total shipments)
        </div>

        <div className="flex items-center space-x-2 self-end sm:self-auto">
          <button
            onClick={() => onPageChange && onPageChange(page - 1)}
            disabled={page <= 1 || loading}
            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            aria-label="Previous Page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="px-3 py-1 font-mono text-slate-300 bg-white/[0.03] rounded-lg border border-white/[0.06]">
            {page} / {totalPages || 1}
          </span>
          <button
            onClick={() => onPageChange && onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            aria-label="Next Page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
