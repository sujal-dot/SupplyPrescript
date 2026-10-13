import React, { useState } from 'react';
import {
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Package,
  AlertTriangle,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';
import GlassButton from '../ui/GlassButton';

export default function InventoryTable({
  inventoryRecords = [],
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
  onSelectProduct,
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
            placeholder="Search product ID or name (e.g. PROD001, STM32)..."
            className="w-full glass-input text-xs pl-10 pr-4 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status filter */}
          <select
            value={filters.inventory_status || ''}
            onChange={(e) => onFilterChange && onFilterChange('inventory_status', e.target.value)}
            className="glass-input text-xs px-3 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-slate-300 focus:outline-none focus:border-cyan-400"
          >
            <option value="">All Inventory Statuses</option>
            <option value="Healthy">Healthy Stock</option>
            <option value="Low">Low Stock</option>
            <option value="Critical">Critical Stock</option>
            <option value="Out of Stock">Out of Stock</option>
          </select>

          {/* Sort By */}
          <select
            value={filters.sort_by || 'product_id'}
            onChange={(e) => onSortChange && onSortChange(e.target.value)}
            className="glass-input text-xs px-3 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-slate-300 focus:outline-none focus:border-cyan-400"
          >
            <option value="product_id">Sort: Product ID</option>
            <option value="inventory_level">Sort: Stock Quantity</option>
            <option value="demand">Sort: Demand</option>
            <option value="reorder_point">Sort: Reorder Point</option>
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
        ) : inventoryRecords.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center text-slate-400">
            <Package className="h-10 w-10 text-slate-500 mb-2" />
            <h4 className="text-sm font-semibold text-slate-300">No Inventory Records</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              No inventory records match your search or status filter.
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono uppercase text-[11px]">
                <th className="py-3 px-4 font-semibold">Product ID</th>
                <th className="py-3 px-4 font-semibold">Product Name</th>
                <th className="py-3 px-4 font-semibold">Inventory Date</th>
                <th className="py-3 px-4 font-semibold">On-Hand Stock</th>
                <th className="py-3 px-4 font-semibold">Projected Demand</th>
                <th className="py-3 px-4 font-semibold">Reorder Threshold</th>
                <th className="py-3 px-4 font-semibold">Safety Stock</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {inventoryRecords.map((item) => {
                const isUnderReorder = Number(item.inventory_level) <= Number(item.reorder_point);
                const isCritical =
                  item.inventory_status === 'Critical' ||
                  item.inventory_status === 'Out of Stock' ||
                  Number(item.inventory_level) < Number(item.safety_stock);

                return (
                  <tr
                    key={item.id || item.product_id}
                    className={`transition-colors ${
                      isCritical
                        ? 'bg-rose-500/[0.03] hover:bg-rose-500/[0.06]'
                        : isUnderReorder
                        ? 'bg-amber-500/[0.02] hover:bg-amber-500/[0.05]'
                        : 'hover:bg-white/[0.03]'
                    }`}
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-white">
                      {item.product_id}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-200">
                      {item.product_name || `Product SKU ${item.product_id}`}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {item.inventory_date || '—'}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      <span
                        className={`font-bold ${
                          isCritical
                            ? 'text-rose-400'
                            : isUnderReorder
                            ? 'text-amber-400'
                            : 'text-white'
                        }`}
                      >
                        {Number(item.inventory_level).toLocaleString()}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {Number(item.demand).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {Number(item.reorder_point).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {Number(item.safety_stock).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge
                        status={item.inventory_status}
                        variant={
                          item.inventory_status === 'Healthy'
                            ? 'success'
                            : item.inventory_status === 'Low'
                            ? 'warning'
                            : 'error'
                        }
                        dot={true}
                      />
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {onSelectProduct && (
                        <button
                          onClick={() => onSelectProduct(item)}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-cyan-300 border border-white/[0.08] hover:border-cyan-400/30 transition-all"
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
          <span className="text-white font-bold">{totalPages || 1}</span> ({total} inventory records)
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
