import React, { useState } from 'react';
import {
  Table,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  AlertCircle,
  HelpCircle,
  Clock,
  CheckCircle2,
  XCircle,
  Info,
} from 'lucide-react';
import FeedbackStatusBadge from './FeedbackStatusBadge';

export default function PredictionErrorTable({
  feedbackData = {},
  selectedStatus = '',
  onStatusChange = () => {},
  selectedModelVersion = '',
  onModelVersionChange = () => {},
  searchTerm = '',
  onSearchChange = () => {},
  currentPage = 1,
  onPageChange = () => {},
  loading = false,
}) {
  const [localSortField, setLocalSortField] = useState('created_at');
  const [localSortDirection, setLocalSortDirection] = useState('desc');

  const items = Array.isArray(feedbackData.items) ? feedbackData.items : [];
  const total = feedbackData.total || 0;
  const page = feedbackData.page || currentPage || 1;
  const totalPages = feedbackData.total_pages || 1;
  const pageSize = feedbackData.page_size || 20;

  const handleSort = (field) => {
    if (localSortField === field) {
      setLocalSortDirection(localSortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setLocalSortField(field);
      setLocalSortDirection('desc');
    }
  };

  // Sort loaded page items
  const sortedItems = [...items].sort((a, b) => {
    let aVal = a[localSortField];
    let bVal = b[localSortField];

    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;

    if (!isNaN(Number(aVal)) && !isNaN(Number(bVal))) {
      aVal = Number(aVal);
      bVal = Number(bVal);
    }

    if (aVal < bVal) return localSortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return localSortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden mb-6">
      {/* Header & Filter Controls */}
      <div className="p-5 border-b border-white/[0.08] flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
            <Table className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Prediction Error Observations & Delivery Feedback
            </h3>
            <p className="text-xs text-slate-400">
              Audit trail of individual predictions matched to final delivery actuals
            </p>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative w-full sm:w-56">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search shipment, prediction..."
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900/80 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 transition-colors"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-1.5">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={selectedStatus}
              onChange={(e) => onStatusChange(e.target.value)}
              aria-label="Filter by Eligibility Status"
              className="bg-slate-900/80 border border-white/10 rounded-xl text-xs text-slate-300 py-1.5 px-2.5 focus:outline-none focus:border-red-500 transition-colors"
            >
              <option value="">All Statuses</option>
              <option value="ELIGIBLE">Eligible</option>
              <option value="PENDING_OUTCOME">Pending Outcome</option>
              <option value="EXCLUDED">Excluded</option>
              <option value="UNDER_REVIEW">Under Review</option>
            </select>
          </div>

          {/* Model Version Filter */}
          <div>
            <select
              value={selectedModelVersion}
              onChange={(e) => onModelVersionChange(e.target.value)}
              aria-label="Filter by Model Version"
              className="bg-slate-900/80 border border-white/10 rounded-xl text-xs text-slate-300 py-1.5 px-2.5 focus:outline-none focus:border-red-500 transition-colors"
            >
              <option value="">All Models</option>
              <option value="v1.0.0">v1.0.0</option>
              <option value="v1.0">v1.0</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-white/[0.08] bg-white/[0.02] text-slate-400 font-medium">
              <th
                onClick={() => handleSort('feedback_id')}
                className="py-3 px-4 cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Feedback / Pred ID</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('shipment_id')}
                className="py-3 px-4 cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Shipment</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('model_version')}
                className="py-3 px-3 cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Model</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('predicted_delay')}
                className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>Predicted</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('actual_delay')}
                className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>Actual</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('prediction_error')}
                className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center justify-end space-x-1" title="actual_delay - predicted_delay (positive = arrived late)">
                  <span>Error (Act - Pred)</span>
                  <HelpCircle className="h-3 w-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('absolute_error')}
                className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>Abs Error</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-500" />
                </div>
              </th>
              <th className="py-3 px-4 text-center">Eligibility Status</th>
              <th className="py-3 px-4">Audit Rationale / Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              <tr>
                <td colSpan="9" className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <Clock className="h-6 w-6 text-red-400 animate-spin" />
                    <span>Loading feedback observations...</span>
                  </div>
                </td>
              </tr>
            ) : sortedItems.length === 0 ? (
              <tr>
                <td colSpan="9" className="py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <AlertCircle className="h-7 w-7 text-slate-600" />
                    <p className="text-sm font-medium text-slate-400">No feedback observations found</p>
                    <p className="text-xs text-slate-600 max-w-sm">
                      Run the pipeline generator above to match stored delay predictions against actual shipment outcomes.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              sortedItems.map((item) => {
                const predDelay = item.predicted_delay != null ? Number(item.predicted_delay) : null;
                const actDelay = item.actual_delay != null ? Number(item.actual_delay) : null;
                const error = item.prediction_error != null ? Number(item.prediction_error) : null;
                const absError = item.absolute_error != null ? Number(item.absolute_error) : null;

                return (
                  <tr
                    key={item.feedback_id || item.prediction_id}
                    className="hover:bg-white/[0.02] transition-colors"
                  >
                    {/* Feedback / Prediction ID */}
                    <td className="py-3 px-4 font-mono text-slate-300">
                      <div className="font-semibold text-white tracking-tight">
                        {item.feedback_id || 'FB-RECORD'}
                      </div>
                      <div className="text-[10px] text-slate-500 truncate max-w-[120px]" title={item.prediction_id}>
                        {item.prediction_id}
                      </div>
                    </td>

                    {/* Shipment */}
                    <td className="py-3 px-4 font-mono text-red-300">
                      {item.shipment_id || 'N/A'}
                    </td>

                    {/* Model Version */}
                    <td className="py-3 px-3">
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                        {item.model_version}
                      </span>
                    </td>

                    {/* Predicted Delay */}
                    <td className="py-3 px-3 text-right font-mono text-slate-200">
                      {predDelay != null ? `${predDelay.toFixed(1)} d` : '—'}
                    </td>

                    {/* Actual Delay */}
                    <td className="py-3 px-3 text-right font-mono">
                      {actDelay != null ? (
                        <span className="text-white font-semibold">{actDelay.toFixed(1)} d</span>
                      ) : (
                        <span className="text-amber-400/80 italic text-[11px]">Pending</span>
                      )}
                    </td>

                    {/* Prediction Error (actual - predicted) */}
                    <td className="py-3 px-3 text-right font-mono">
                      {error != null ? (
                        <span
                          className={`inline-flex items-center justify-end font-semibold ${
                            error > 0
                              ? 'text-rose-400'
                              : error < 0
                              ? 'text-emerald-400'
                              : 'text-slate-400'
                          }`}
                          title={
                            error > 0
                              ? 'Underpredicted: Arrived later than model estimated'
                              : error < 0
                              ? 'Overpredicted: Arrived earlier than model estimated'
                              : 'Exact prediction match'
                          }
                        >
                          {error > 0 ? `+${error.toFixed(1)} d` : `${error.toFixed(1)} d`}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    {/* Absolute Error */}
                    <td className="py-3 px-3 text-right font-mono text-slate-300">
                      {absError != null ? `${absError.toFixed(1)} d` : '—'}
                    </td>

                    {/* Status Badge */}
                    <td className="py-3 px-4 text-center">
                      <FeedbackStatusBadge status={item.feedback_status} size="sm" />
                    </td>

                    {/* Exclusion / Reason Notes */}
                    <td className="py-3 px-4 text-slate-400 max-w-xs truncate" title={item.exclusion_reason || item.notes || ''}>
                      {item.exclusion_reason ? (
                        <span className="text-rose-300/90 text-[11px] flex items-center space-x-1">
                          <Info className="h-3 w-3 text-rose-400 flex-shrink-0 inline" />
                          <span className="truncate">{item.exclusion_reason}</span>
                        </span>
                      ) : item.feedback_status === 'PENDING_OUTCOME' ? (
                        <span className="text-amber-400/80 text-[11px]">Awaiting operational delivery</span>
                      ) : item.notes ? (
                        <span className="text-slate-400 text-[11px]">{item.notes}</span>
                      ) : (
                        <span className="text-slate-600 text-[11px]">Verified ground truth</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
        <div>
          Showing{' '}
          <span className="font-semibold text-white">
            {total > 0 ? (page - 1) * pageSize + 1 : 0}
          </span>{' '}
          to{' '}
          <span className="font-semibold text-white">
            {Math.min(page * pageSize, total)}
          </span>{' '}
          of <span className="font-semibold text-white">{total.toLocaleString()}</span> records
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || loading}
            aria-label="Previous Page"
            className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="font-mono px-2 py-1 text-slate-300">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
            aria-label="Next Page"
            className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
