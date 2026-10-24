import React, { useState } from 'react';
import {
  History,
  ShieldCheck,
  RefreshCw,
  ExternalLink,
  Clock,
  DollarSign,
  CheckCircle2,
  AlertCircle,
  FileText,
  User,
  ChevronLeft,
  ChevronRight,
  Eye,
  BarChart3,
  TrendingUp,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';
import DecisionDetailModal from './DecisionDetailModal';

export default function DecisionHistory({
  decisions = [],
  loading = false,
  onRefresh,
  activeShipmentId = null,
  showAllShipments = false,
  onToggleShowAll,
  // Pagination props
  page = 1,
  pageSize = 10,
  total = null,
  onPageChange = null,
  onPageSizeChange = null,
}) {
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTab, setModalTab] = useState('details');

  const formatCost = (val) => {
    if (val == null) return '—';
    return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const handleOpenDetail = (dec, tab = 'details') => {
    setSelectedDecision(dec);
    setModalTab(tab);
    setModalOpen(true);
  };

  const handleCloseDetail = () => {
    setModalOpen(false);
    setSelectedDecision(null);
    setModalTab('details');
  };

  // Derive total count
  const effectiveTotal = total != null ? total : decisions.length;
  const totalPages = Math.max(1, Math.ceil(effectiveTotal / pageSize));
  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, effectiveTotal);

  // If onPageChange is provided, assume decisions is already paged from backend;
  // otherwise, do client-side slicing for standalone usage.
  const displayDecisions = onPageChange ? decisions : decisions.slice(startIndex, endIndex);

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/[0.06] flex flex-wrap items-center justify-between gap-3 bg-white/[0.01]">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <History className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight flex items-center space-x-2">
              <span>Decision Execution Audit Trail</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-300 border border-white/[0.08]">
                {effectiveTotal} recorded
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Immutable PostgreSQL ledger of authorized supply-chain decisions and external dispatch statuses
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {onToggleShowAll && activeShipmentId && (
            <button
              onClick={onToggleShowAll}
              className="text-xs text-red-300 hover:text-red-200 underline underline-offset-2 px-2 py-1 transition-colors"
            >
              {showAllShipments ? `Filter to ${activeShipmentId}` : 'Show all shipments'}
            </button>
          )}

          <GlassButton
            variant="outline"
            size="sm"
            icon={RefreshCw}
            onClick={onRefresh}
            loading={loading}
          >
            Refresh History
          </GlassButton>
        </div>
      </div>

      {/* Decision Table */}
      {loading && displayDecisions.length === 0 ? (
        <div className="p-8 text-center text-xs text-slate-400 space-y-2">
          <RefreshCw className="h-5 w-5 animate-spin mx-auto text-red-400" />
          <p>Retrieving decision audit trail from database...</p>
        </div>
      ) : displayDecisions.length === 0 ? (
        <div className="p-10 text-center flex flex-col items-center justify-center">
          <div className="p-3 rounded-2xl bg-white/[0.04] text-slate-400 mb-2 border border-white/[0.06]">
            <History className="h-6 w-6" />
          </div>
          <h4 className="text-sm font-bold text-white">No Decisions Recorded Yet</h4>
          <p className="text-xs text-slate-400 max-w-sm mt-1">
            {activeShipmentId && !showAllShipments
              ? `No authorized execution decisions have been logged for shipment ${activeShipmentId}. Select a feasible alternative and click "EXECUTE DECISION".`
              : 'No decisions have been executed yet. Select a shipment, evaluate alternatives, and execute an authorized decision.'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] text-slate-400 uppercase tracking-wider font-mono text-[10px] bg-white/[0.02]">
                <th className="py-3 px-4 font-semibold">Decision ID</th>
                <th className="py-3 px-4 font-semibold">Shipment</th>
                <th className="py-3 px-4 font-semibold">User</th>
                <th className="py-3 px-4 font-semibold">Recommendation</th>
                <th className="py-3 px-4 font-semibold">Predicted Cost</th>
                <th className="py-3 px-4 font-semibold">Predicted Delay</th>
                <th className="py-3 px-4 font-semibold">Internal Status</th>
                <th className="py-3 px-4 font-semibold">External Dispatch</th>
                <th className="py-3 px-4 font-semibold">Recorded At</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {displayDecisions.map((dec) => {
                const rec = dec.recommendation || dec.strategy || dec.decision || '—';
                const cost = dec.predicted_cost ?? dec.estimated_total_cost;
                const delay = dec.predicted_delay ?? dec.estimated_delay_days;
                const transit = dec.estimated_delivery_days;
                const user = dec.user_id || dec.approved_by || 'usr_ops_manager';
                const timestamp = dec.decision_time || dec.created_at;

                return (
                  <tr
                    key={dec.decision_id}
                    className="hover:bg-white/[0.02] transition-colors"
                  >
                    {/* Decision ID */}
                    <td className="py-3.5 px-4 font-mono font-bold text-red-300">
                      <button
                        onClick={() => handleOpenDetail(dec)}
                        className="hover:underline flex items-center space-x-1 text-left"
                        title="View Full Decision Record"
                      >
                        <span>{dec.decision_id}</span>
                      </button>
                    </td>

                    {/* Target Shipment */}
                    <td className="py-3.5 px-4 font-mono text-white font-medium">
                      {dec.shipment_id}
                    </td>

                    {/* User ID */}
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      <div className="flex items-center space-x-1" title={user}>
                        <User className="h-3 w-3 text-slate-400 flex-shrink-0" />
                        <span className="truncate max-w-[90px]">{user}</span>
                      </div>
                    </td>

                    {/* Strategy & Option */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-1.5">
                        {dec.option_id && (
                          <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/10 text-red-300 border border-red-500/20">
                            {dec.option_id}
                          </span>
                        )}
                        <span className="font-semibold text-slate-200">
                          {rec}
                        </span>
                      </div>
                      {dec.decision_reason && (
                        <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5 max-w-xs">
                          {dec.decision_reason}
                        </p>
                      )}
                    </td>

                    {/* Cost */}
                    <td className="py-3.5 px-4 font-mono text-slate-200 font-bold">
                      {formatCost(cost)}
                    </td>

                    {/* Delivery / Delay Time */}
                    <td className="py-3.5 px-4 font-mono text-red-300">
                      {delay != null ? (
                        <span>{`${Number(delay).toFixed(1)}d delay`}</span>
                      ) : transit != null ? (
                        <span>{`${Number(transit).toFixed(1)}d transit`}</span>
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* Internal Lifecycle Status */}
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        <CheckCircle2 className="h-3 w-3 inline text-emerald-400" />
                        <span>{dec.status || 'RECORDED'}</span>
                      </span>
                    </td>

                    {/* External Dispatch Status (Safe Boundary Marker) */}
                    <td className="py-3.5 px-4">
                      <span
                        className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700"
                        title="Decisions are logged for authorization and do not execute automated freight bookings or disbursements."
                      >
                        <ShieldCheck className="h-3 w-3 text-red-400" />
                        <span>{dec.external_action_status || 'NOT_EXECUTED'}</span>
                      </span>
                    </td>

                    {/* Recorded At */}
                    <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                      {formatDate(timestamp)}
                    </td>

                    {/* Action Buttons */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => handleOpenDetail(dec, 'details')}
                          className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-medium text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-colors"
                          title="View Decision Write-Back Details"
                        >
                          <Eye className="h-3 w-3" />
                          <span>Details</span>
                        </button>
                        <button
                          onClick={() => handleOpenDetail(dec, 'outcome')}
                          className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-medium text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 transition-colors"
                          title="View or Record Closed-Loop Operational Actuals"
                        >
                          <BarChart3 className="h-3 w-3" />
                          <span>Outcome</span>
                        </button>
                        <button
                          onClick={() => handleOpenDetail(dec, 'roi')}
                          className="inline-flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-medium text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 transition-colors"
                          title="View Decision ROI & Success Analytics"
                        >
                          <TrendingUp className="h-3 w-3" />
                          <span>ROI</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Controls */}
      {effectiveTotal > 0 && (
        <div className="p-4 border-t border-white/[0.06] flex flex-wrap items-center justify-between gap-3 bg-white/[0.01] text-xs text-slate-400">
          <div className="font-mono text-[11px]">
            Showing <span className="text-white font-bold">{Math.min(startIndex + 1, effectiveTotal)}</span> to{' '}
            <span className="text-white font-bold">{endIndex}</span> of{' '}
            <span className="text-white font-bold">{effectiveTotal}</span> decisions
          </div>

          <div className="flex items-center space-x-3">
            {onPageSizeChange && (
              <div className="flex items-center space-x-1.5 font-mono text-[11px]">
                <span>Show:</span>
                <select
                  value={pageSize}
                  onChange={(e) => onPageSizeChange(Number(e.target.value))}
                  className="bg-slate-800 border border-white/[0.08] text-slate-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-red-500"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
              </div>
            )}

            <div className="flex items-center space-x-1 font-mono text-[11px]">
              <span>Page {page} of {totalPages}</span>
            </div>

            <div className="flex items-center space-x-1.5">
              <button
                onClick={() => onPageChange && onPageChange(page - 1)}
                disabled={page <= 1}
                className="p-1.5 rounded-lg border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Previous Page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => onPageChange && onPageChange(page + 1)}
                disabled={page >= totalPages}
                className="p-1.5 rounded-lg border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Next Page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decision Detail Modal */}
      <DecisionDetailModal
        isOpen={modalOpen}
        onClose={handleCloseDetail}
        decisionId={selectedDecision?.decision_id}
        initialData={selectedDecision}
        initialTab={modalTab}
      />
    </div>
  );
}
