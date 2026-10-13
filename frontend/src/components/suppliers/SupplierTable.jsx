import React, { useState } from 'react';
import {
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Award,
  Building2,
  AlertCircle,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';

export default function SupplierTable({
  suppliers = [],
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
  onSelectSupplier,
  filters = {},
}) {
  const [searchTerm, setSearchTerm] = useState(filters.search || '');

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (onSearchChange) onSearchChange(searchTerm);
  };

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Top Filter Controls */}
      <div className="p-4 sm:p-5 border-b border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onBlur={() => onSearchChange && onSearchChange(searchTerm)}
            placeholder="Search supplier name or ID (e.g. Apex, SUP001)..."
            className="w-full glass-input text-xs pl-10 pr-4 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2">
          {/* Minimum reliability filter */}
          <select
            value={filters.min_reliability !== undefined ? String(filters.min_reliability) : ''}
            onChange={(e) => {
              const val = e.target.value;
              onFilterChange && onFilterChange('min_reliability', val === '' ? null : parseFloat(val));
            }}
            className="glass-input text-xs px-3 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-slate-300 focus:outline-none focus:border-cyan-400"
          >
            <option value="">All Reliability Tiers</option>
            <option value="0.95">&ge; 95% High Reliability</option>
            <option value="0.90">&ge; 90% Moderate Reliability</option>
            <option value="0.80">&ge; 80% Minimum Threshold</option>
          </select>

          {/* Sort By */}
          <select
            value={filters.sort_by || 'supplier_id'}
            onChange={(e) => onSortChange && onSortChange(e.target.value)}
            className="glass-input text-xs px-3 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-slate-300 focus:outline-none focus:border-cyan-400"
          >
            <option value="supplier_id">Sort: Supplier ID</option>
            <option value="reliability">Sort: Highest Reliability</option>
            <option value="supplier_name">Sort: Supplier Name</option>
          </select>

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
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 bg-white/5 rounded-xl w-full" />
            ))}
          </div>
        ) : suppliers.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center text-slate-400">
            <Building2 className="h-10 w-10 text-slate-500 mb-2" />
            <h4 className="text-sm font-semibold text-slate-300">No Suppliers Found</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              No supplier records matched your search or reliability filter.
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono uppercase text-[11px]">
                <th className="py-3 px-4 font-semibold">Supplier ID</th>
                <th className="py-3 px-4 font-semibold">Supplier Name</th>
                <th className="py-3 px-4 font-semibold">Origin Hub</th>
                <th className="py-3 px-4 font-semibold">Reliability Score</th>
                <th className="py-3 px-4 font-semibold">Total Shipments</th>
                <th className="py-3 px-4 font-semibold">Hist. Avg Delay</th>
                <th className="py-3 px-4 font-semibold">Delayed Orders</th>
                <th className="py-3 px-4 font-semibold text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {suppliers.map((s) => {
                const rawRel = s.supplier_reliability;
                let formattedRel = 'Unavailable';
                let relPct = null;

                if (rawRel !== null && rawRel !== undefined) {
                  const num = Number(rawRel);
                  if (!isNaN(num)) {
                    relPct = num <= 1.0 ? Math.round(num * 1000) / 10 : Math.round(num * 10) / 10;
                    formattedRel = `${relPct}%`;
                  }
                }

                return (
                  <tr
                    key={s.supplier_id}
                    className="hover:bg-white/[0.03] transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-white">
                      {s.supplier_id}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-200">
                      {s.supplier_name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">
                      {s.origin || '—'}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      {relPct !== null ? (
                        <div className="flex items-center space-x-2">
                          <span
                            className={
                              relPct >= 95
                                ? 'text-emerald-400 font-bold'
                                : relPct >= 85
                                ? 'text-cyan-300 font-semibold'
                                : 'text-amber-400'
                            }
                          >
                            {formattedRel}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">Unavailable</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {s.total_shipments !== undefined && s.total_shipments !== null
                        ? Number(s.total_shipments).toLocaleString()
                        : '—'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {s.historical_avg_delay !== undefined && s.historical_avg_delay !== null
                        ? `${Number(s.historical_avg_delay).toFixed(2)} d`
                        : '—'}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      {s.delayed_shipment_count !== undefined && s.delayed_shipment_count !== null ? (
                        <span className={s.delayed_shipment_count > 0 ? 'text-amber-300' : 'text-slate-400'}>
                          {s.delayed_shipment_count}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {onSelectSupplier && (
                        <button
                          onClick={() => onSelectSupplier(s)}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-cyan-300 border border-white/[0.08] hover:border-cyan-400/30 transition-all"
                        >
                          <span>Profile</span>
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
          <span className="text-white font-bold">{totalPages || 1}</span> ({total} suppliers)
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
