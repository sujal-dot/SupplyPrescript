import React, { useState } from 'react';
import {
  FileText,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Search,
  ArrowUpDown,
  AlertCircle,
  Clock,
  DollarSign,
} from 'lucide-react';
import DecisionSuccessBadge from './DecisionSuccessBadge';

export default function DecisionPerformanceTable({
  performancePage = {},
  onPageChange = () => {},
  onSelectDecision = () => {},
  currency = 'USD',
  loading = false,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState('decision_time');
  const [sortDirection, setSortDirection] = useState('desc');

  const page = performancePage.page || 1;
  const pageSize = performancePage.page_size || 20;
  const total = performancePage.total || 0;
  const totalPages = performancePage.total_pages || 1;
  const items = Array.isArray(performancePage.items) ? performancePage.items : [];

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Local client filtering on currently loaded page items
  const filteredItems = items.filter((item) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (item.decision_id && item.decision_id.toLowerCase().includes(term)) ||
      (item.shipment_id && item.shipment_id.toLowerCase().includes(term)) ||
      (item.strategy && item.strategy.toLowerCase().includes(term)) ||
      (item.decision_name && item.decision_name.toLowerCase().includes(term))
    );
  });

  // Client sort on currently loaded items
  const sortedItems = [...filteredItems].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];

    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;

    // Convert numbers if numeric
    if (!isNaN(Number(aVal)) && !isNaN(Number(bVal))) {
      aVal = Number(aVal);
      bVal = Number(bVal);
    }

    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden mb-6">
      {/* Table Header Controls */}
      <div className="p-5 border-b border-white/[0.08] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
            <FileText className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Decision Outcome Audit Trail & Performance Records
            </h3>
            <p className="text-xs text-slate-400">
              Granular closed-loop audit of predicted versus actual financial and delivery outcomes
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search decisions, shipments..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-900/80 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 transition-colors"
          />
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="bg-white/[0.02] border-b border-white/[0.06] text-slate-400 font-semibold uppercase tracking-wider">
              <th className="py-3 px-4 cursor-pointer hover:text-white" onClick={() => handleSort('decision_id')}>
                <div className="flex items-center space-x-1">
                  <span>Decision / Shipment</span>
                  <ArrowUpDown className="h-3 w-3" />
                </div>
              </th>
              <th className="py-3 px-3">Strategy</th>
              <th className="py-3 px-3 cursor-pointer hover:text-white" onClick={() => handleSort('decision_time')}>
                <div className="flex items-center space-x-1">
                  <span>Decision Time</span>
                  <ArrowUpDown className="h-3 w-3" />
                </div>
              </th>
              <th className="py-3 px-3 text-center">Outcome Status</th>
              <th className="py-3 px-3 text-right cursor-pointer hover:text-white" onClick={() => handleSort('cost_difference')}>
                <div className="flex items-center justify-end space-x-1">
                  <span>Cost (Pred / Act)</span>
                  <ArrowUpDown className="h-3 w-3" />
                </div>
              </th>
              <th className="py-3 px-3 text-right">Cost Diff</th>
              <th className="py-3 px-3 text-right">Delay (Pred / Act)</th>
              <th className="py-3 px-3 text-right">Baseline Savings</th>
              <th className="py-3 px-3 text-center">ROI %</th>
              <th className="py-3 px-4 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td colSpan={10} className="py-4 px-4">
                    <div className="h-4 bg-white/5 rounded w-full" />
                  </td>
                </tr>
              ))
            ) : sortedItems.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-slate-400">
                  <AlertCircle className="h-6 w-6 text-slate-500 mx-auto mb-2" />
                  <p className="font-semibold text-slate-300">No matching decision records found</p>
                  <p className="text-[11px] text-slate-500 mt-1">Try modifying your search or filter criteria.</p>
                </td>
              </tr>
            ) : (
              sortedItems.map((row) => {
                const costDiffNum = row.cost_difference != null ? Number(row.cost_difference) : null;
                const isUnderBudget = costDiffNum != null && costDiffNum < 0;
                const isOverrun = costDiffNum != null && costDiffNum > 0;

                const delayDiffNum = row.delay_difference != null ? Number(row.delay_difference) : null;
                const isEarlier = delayDiffNum != null && delayDiffNum < 0;
                const isLater = delayDiffNum != null && delayDiffNum > 0;

                return (
                  <tr
                    key={row.decision_id || row.db_id}
                    className="hover:bg-white/[0.02] transition-colors group cursor-pointer"
                    onClick={() => onSelectDecision(row)}
                  >
                    {/* Decision ID & Shipment */}
                    <td className="py-3.5 px-4">
                      <div className="font-mono font-semibold text-white group-hover:text-red-300 transition-colors">
                        {row.decision_id}
                      </div>
                      <div className="text-[11px] font-mono text-red-400/80">
                        {row.shipment_id || 'No Shipment'}
                      </div>
                    </td>

                    {/* Strategy */}
                    <td className="py-3.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-white/[0.05] border border-white/10 text-slate-300">
                        {row.strategy ? row.strategy.replace(/_/g, ' ') : 'Standard'}
                      </span>
                    </td>

                    {/* Decision Time */}
                    <td className="py-3.5 px-3 text-slate-400 text-[11px]">
                      {row.decision_time ? new Date(row.decision_time).toLocaleDateString() : 'N/A'}
                    </td>

                    {/* Outcome Status */}
                    <td className="py-3.5 px-3 text-center">
                      <DecisionSuccessBadge status={row.evaluation_status} size="sm" />
                    </td>

                    {/* Predicted vs Actual Cost */}
                    <td className="py-3.5 px-3 text-right font-mono">
                      <div className="text-slate-400">
                        {row.predicted_cost ? `$${Number(row.predicted_cost).toLocaleString()}` : '—'}
                      </div>
                      <div className="text-white font-semibold">
                        {row.actual_cost ? `$${Number(row.actual_cost).toLocaleString()}` : <span className="text-amber-400 text-[11px]">Pending</span>}
                      </div>
                    </td>

                    {/* Cost Diff */}
                    <td className="py-3.5 px-3 text-right font-mono">
                      {costDiffNum != null ? (
                        <span className={`font-semibold ${isUnderBudget ? 'text-emerald-400' : isOverrun ? 'text-rose-400' : 'text-slate-300'}`}>
                          {costDiffNum > 0 ? '+' : ''}${costDiffNum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>

                    {/* Delay Diff */}
                    <td className="py-3.5 px-3 text-right font-mono">
                      <div className="text-slate-400">
                        {row.predicted_delay != null ? `${row.predicted_delay}d` : '—'} / {row.actual_delay != null ? `${row.actual_delay}d` : '—'}
                      </div>
                      {delayDiffNum != null ? (
                        <div className={`text-[11px] font-semibold ${isEarlier ? 'text-emerald-400' : isLater ? 'text-rose-400' : 'text-slate-300'}`}>
                          {delayDiffNum > 0 ? `+${delayDiffNum}d` : `${delayDiffNum}d`}
                        </div>
                      ) : null}
                    </td>

                    {/* Baseline Savings */}
                    <td className="py-3.5 px-3 text-right font-mono">
                      {row.baseline_savings != null ? (
                        <span className="text-emerald-400 font-semibold">
                          ${Number(row.baseline_savings).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>

                    {/* ROI % */}
                    <td className="py-3.5 px-3 text-center font-mono">
                      {row.roi_status === 'CALCULATED' && row.roi_percentage != null ? (
                        <span className="text-emerald-400 font-bold">
                          {row.roi_percentage > 0 ? '+' : ''}{row.roi_percentage.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-slate-500 text-[11px]">N/A</span>
                      )}
                    </td>

                    {/* Action */}
                    <td className="py-3.5 px-4 text-center">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDecision(row);
                        }}
                        className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-colors inline-flex items-center space-x-1"
                        title="View Full ROI & Outcome Details"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        <span className="text-[10px]">Details</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-white/[0.06] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
        <div>
          Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
          {Math.min(page * pageSize, total)} of {total.toLocaleString()} decisions
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || loading}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed border border-white/[0.08] transition-colors"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            <span>Previous</span>
          </button>
          <span className="px-2 font-mono text-slate-300">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed border border-white/[0.08] transition-colors"
          >
            <span>Next</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
