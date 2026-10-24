import React, { useEffect, useState } from 'react';
import {
  X,
  ShieldCheck,
  CheckCircle2,
  Clock,
  DollarSign,
  Truck,
  Hash,
  User,
  Key,
  Layers,
  FileText,
  AlertTriangle,
  RefreshCw,
  Copy,
  Check,
  PlusCircle,
  BarChart3,
  TrendingUp,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';
import { getDecisionById, getOutcome, getDecisionROI } from '../../services/decisionService';
import PredictedActualComparison from '../outcomes/PredictedActualComparison';
import OutcomeEntryModal from '../outcomes/OutcomeEntryModal';
import OutcomeStatusBadge from '../outcomes/OutcomeStatusBadge';
import DecisionROISummary from '../roi/DecisionROISummary';

export default function DecisionDetailModal({
  isOpen,
  onClose,
  decisionId,
  initialData = null,
  initialTab = 'details',
}) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab);

  // Day 19 Closed-Loop Outcome State
  const [outcomeComparison, setOutcomeComparison] = useState(null);
  const [loadingOutcome, setLoadingOutcome] = useState(false);
  const [outcomeEntryOpen, setOutcomeEntryOpen] = useState(false);

  // Day 20 Decision ROI Engine State
  const [roiData, setRoiData] = useState(null);
  const [loadingROI, setLoadingROI] = useState(false);
  const [roiError, setRoiError] = useState(null);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab, isOpen]);

  const fetchROI = async () => {
    if (!decisionId) return;
    setLoadingROI(true);
    setRoiError(null);
    try {
      const res = await getDecisionROI(decisionId);
      setRoiData(res);
    } catch (err) {
      console.warn('Failed to fetch decision ROI data:', err);
      setRoiError(err.response?.data?.detail || err.message || 'Failed to calculate decision ROI');
    } finally {
      setLoadingROI(false);
    }
  };

  useEffect(() => {
    if (!isOpen || !decisionId) return;

    let mounted = true;
    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getDecisionById(decisionId);
        if (mounted) {
          setData(result);
        }
      } catch (err) {
        if (mounted) {
          console.warn('Failed to fetch full decision details, using initial data:', err);
          if (initialData) {
            setData(initialData);
          } else {
            setError(err.response?.data?.detail || err.message || 'Failed to load decision');
          }
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    const fetchOutcomeComparison = async () => {
      setLoadingOutcome(true);
      try {
        const res = await getOutcome(decisionId);
        if (mounted) {
          setOutcomeComparison(res);
        }
      } catch (err) {
        // 404 is expected when outcome has not been recorded yet
        if (mounted) {
          setOutcomeComparison(null);
        }
      } finally {
        if (mounted) setLoadingOutcome(false);
      }
    };

    const loadROI = async () => {
      setLoadingROI(true);
      setRoiError(null);
      try {
        const res = await getDecisionROI(decisionId);
        if (mounted) {
          setRoiData(res);
        }
      } catch (err) {
        if (mounted) {
          console.warn('Failed to fetch decision ROI data:', err);
          setRoiError(err.response?.data?.detail || err.message || 'Failed to calculate decision ROI');
        }
      } finally {
        if (mounted) setLoadingROI(false);
      }
    };

    fetchDetail();
    fetchOutcomeComparison();
    loadROI();

    return () => {
      mounted = false;
    };
  }, [isOpen, decisionId, initialData]);

  if (!isOpen) return null;

  const current = data || initialData || {};

  const formatCost = (val) => {
    if (val == null) return '—';
    return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString([], {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short',
      });
    } catch {
      return isoStr;
    }
  };

  const handleCopyId = (text) => {
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const rec = current.recommendation || current.strategy || current.decision || '—';
  const predictedCost = current.predicted_cost ?? current.estimated_total_cost;
  const predictedDelay = current.predicted_delay ?? current.estimated_delay_days;
  const decisionTime = current.decision_time || current.created_at;
  const userId = current.user_id || current.approved_by || 'usr_ops_manager';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="glass-card w-full max-w-3xl rounded-[28px] border border-white/[0.16] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8),inset_0_1px_1.5px_rgba(255,255,255,0.35)] overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="decision-detail-title"
      >
        {/* Header */}
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-2xl bg-red-500/20 text-red-300 border border-red-500/30 shadow-[inset_0_1px_1px_rgba(255,255,255,0.25)]">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 id="decision-detail-title" className="text-base font-bold text-white tracking-tight">
                  Decision Record Details
                </h3>
                <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-red-500/20 text-red-200 border border-white/15 shadow-[inset_0_1px_0.5px_rgba(255,255,255,0.30)]">
                  {current.decision_id || decisionId}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Target Shipment: <span className="font-mono text-white">{current.shipment_id || '—'}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-white/[0.08] border border-transparent hover:border-white/15 transition-all"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Apple Segmented Pill Tab Navigation */}
        <div className="px-5 pt-3 pb-2 border-b border-white/[0.06] bg-white/[0.01]">
          <div className="inline-flex p-1 rounded-full bg-black/40 border border-white/10 shadow-[inset_0_1px_2px_rgba(0,0,0,0.5)] backdrop-blur-md">
            <button
              onClick={() => setActiveTab('details')}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-full transition-all flex items-center space-x-1.5 ${
                activeTab === 'details'
                  ? 'bg-white/15 text-white border border-white/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.30),0_2px_8px_rgba(0,0,0,0.3)]'
                  : 'text-slate-400 hover:text-white border border-transparent'
              }`}
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Decision Write-Back Record</span>
            </button>

            <button
              onClick={() => setActiveTab('outcome')}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-full transition-all flex items-center space-x-1.5 ${
                activeTab === 'outcome'
                  ? 'bg-white/15 text-white border border-white/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.30),0_2px_8px_rgba(0,0,0,0.3)]'
                  : 'text-slate-400 hover:text-white border border-transparent'
              }`}
            >
              <BarChart3 className="h-3.5 w-3.5" />
              <span>Closed-Loop Outcome Tracking</span>
              {outcomeComparison?.actual ? (
                <span className="ml-1 w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)] inline-block" />
              ) : (
                <span className="ml-1 text-[9px] px-1.5 py-0.2 rounded-full bg-white/[0.08] text-slate-400">
                  Pending
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('roi')}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-full transition-all flex items-center space-x-1.5 ${
                activeTab === 'roi'
                  ? 'bg-white/15 text-white border border-white/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.30),0_2px_8px_rgba(0,0,0,0.3)]'
                  : 'text-slate-400 hover:text-white border border-transparent'
              }`}
            >
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Decision ROI Engine</span>
              {roiData?.roi?.status === 'CALCULATED' ? (
                <span className="ml-1 w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)] inline-block" />
              ) : null}
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {activeTab === 'details' && (
            <>
              {loading && !data ? (
                <div className="py-12 text-center text-xs text-slate-400 space-y-2">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto text-red-400" />
                  <p>Fetching immutable record from PostgreSQL...</p>
                </div>
              ) : error && !data ? (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                  {error}
                </div>
              ) : (
                <>
                  {/* Top Summary Banner */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                    <div>
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Status</div>
                      <div className="mt-1 inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        <CheckCircle2 className="h-3 w-3" />
                        <span>{current.status || 'RECORDED'}</span>
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Predicted Cost</div>
                      <div className="mt-1 text-sm font-mono font-bold text-white">
                        {formatCost(predictedCost)}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Predicted Delay</div>
                      <div className="mt-1 text-sm font-mono font-bold text-red-300">
                        {predictedDelay != null ? `${Number(predictedDelay).toFixed(1)} days` : '0.0 days'}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">External Dispatch</div>
                      <div className="mt-1 inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                        <ShieldCheck className="h-3 w-3 text-red-400" />
                        <span>{current.external_action_status || 'NOT_EXECUTED'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Data Contract Details */}
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono flex items-center space-x-2">
                      <Layers className="h-4 w-4 text-red-400" />
                      <span>Write-Back Schema &amp; Data Contract</span>
                    </h4>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      {/* Decision ID */}
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                        <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between">
                          <span className="flex items-center space-x-1">
                            <Hash className="h-3 w-3 text-red-400" />
                            <span>Decision ID</span>
                          </span>
                          <button
                            onClick={() => handleCopyId(current.decision_id)}
                            className="text-red-400 hover:text-red-300 p-0.5"
                            title="Copy Decision ID"
                          >
                            {copiedKey ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                          </button>
                        </div>
                        <div className="mt-1 font-mono font-semibold text-white">
                          {current.decision_id}
                        </div>
                      </div>

                      {/* Target Shipment */}
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                        <div className="text-[10px] text-slate-400 font-mono flex items-center space-x-1">
                          <Truck className="h-3 w-3 text-red-400" />
                          <span>Shipment ID</span>
                        </div>
                        <div className="mt-1 font-mono font-semibold text-white">
                          {current.shipment_id}
                        </div>
                      </div>

                      {/* User ID */}
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                        <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between">
                          <span className="flex items-center space-x-1">
                            <User className="h-3 w-3 text-red-400" />
                            <span>User ID</span>
                          </span>
                          <span className="text-[9px] px-1 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                            Dev Mode Unverified
                          </span>
                        </div>
                        <div className="mt-1 font-mono font-semibold text-slate-200">
                          {userId}
                        </div>
                      </div>

                      {/* Recommendation / Strategy */}
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                        <div className="text-[10px] text-slate-400 font-mono flex items-center space-x-1">
                          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                          <span>Recommendation</span>
                        </div>
                        <div className="mt-1 font-semibold text-white flex items-center space-x-1.5">
                          {current.option_id && (
                            <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 border border-red-500/20">
                              {current.option_id}
                            </span>
                          )}
                          <span>{rec}</span>
                        </div>
                      </div>

                      {/* Decision Time */}
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] sm:col-span-2">
                        <div className="text-[10px] text-slate-400 font-mono flex items-center space-x-1">
                          <Clock className="h-3 w-3 text-red-400" />
                          <span>Decision Timestamp (Timezone-Aware)</span>
                        </div>
                        <div className="mt-1 font-mono text-slate-200">
                          {formatDate(decisionTime)}
                        </div>
                      </div>

                      {/* Idempotency Key */}
                      {current.idempotency_key && (
                        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] sm:col-span-2">
                          <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between">
                            <span className="flex items-center space-x-1">
                              <Key className="h-3 w-3 text-red-400" />
                              <span>Idempotency Key</span>
                            </span>
                            <span className="text-[9px] px-1 rounded bg-red-500/10 text-red-300 border border-red-500/20">
                              Unique DB Index
                            </span>
                          </div>
                          <div className="mt-1 font-mono text-slate-300 break-all">
                            {current.idempotency_key}
                          </div>
                        </div>
                      )}

                      {/* Optimization Run ID */}
                      {current.optimization_run_id && (
                        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] sm:col-span-2">
                          <div className="text-[10px] text-slate-400 font-mono">
                            Optimization Run ID
                          </div>
                          <div className="mt-1 font-mono text-slate-300 break-all">
                            {current.optimization_run_id}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Safety Boundary Notice */}
                  <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 flex items-start space-x-2.5 text-xs text-slate-300">
                    <ShieldCheck className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <div className="font-semibold text-slate-200">
                        Operational Governance Safety Boundary
                      </div>
                      <p className="text-[11px] text-slate-400 leading-normal">
                        This decision has been written to PostgreSQL with status <span className="font-mono text-emerald-300 font-bold">RECORDED</span>.
                        External carrier booking and payment execution remain strictly <span className="font-mono text-slate-200 font-bold">NOT_EXECUTED</span>.
                      </p>
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {activeTab === 'outcome' && (
            <div className="space-y-4">
              {loadingOutcome ? (
                <div className="py-12 text-center text-xs text-slate-400 space-y-2">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto text-red-400" />
                  <p>Loading closed-loop outcome comparison...</p>
                </div>
              ) : outcomeComparison?.actual ? (
                <PredictedActualComparison comparison={outcomeComparison} />
              ) : (
                <div className="p-8 text-center flex flex-col items-center justify-center rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                  <div className="p-3.5 rounded-2xl bg-red-500/10 text-red-400 border border-red-500/20">
                    <Clock className="h-6 w-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">No Actual Outcome Recorded Yet</h4>
                    <p className="text-xs text-slate-400 max-w-sm mt-1">
                      This decision has been authorized and committed, but operational fulfillment actuals (cost, delivery date, supplier, quantity) have not yet been recorded.
                    </p>
                  </div>
                  <GlassButton
                    variant="primary"
                    size="sm"
                    icon={PlusCircle}
                    onClick={() => setOutcomeEntryOpen(true)}
                  >
                    Record Actual Outcome
                  </GlassButton>
                </div>
              )}
            </div>
          )}
          {activeTab === 'roi' && (
            <div className="space-y-4">
              <DecisionROISummary
                roiData={roiData}
                comparison={outcomeComparison}
                loading={loadingROI}
                error={roiError}
                onRefresh={fetchROI}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/[0.08] flex items-center justify-between bg-white/[0.02]">
          <div>
            {activeTab === 'outcome' && !outcomeComparison?.actual && (
              <GlassButton
                variant="primary"
                size="sm"
                icon={PlusCircle}
                onClick={() => setOutcomeEntryOpen(true)}
              >
                Add Actual Outcome
              </GlassButton>
            )}
          </div>
          <GlassButton variant="outline" size="sm" onClick={onClose}>
            Close Record
          </GlassButton>
        </div>
      </div>

      {/* Outcome Entry Modal */}
      <OutcomeEntryModal
        isOpen={outcomeEntryOpen}
        onClose={() => setOutcomeEntryOpen(false)}
        decision={current}
        onSuccess={(updatedComparison) => {
          setOutcomeComparison(updatedComparison);
          fetchROI();
          setActiveTab('outcome');
        }}
      />
    </div>
  );
}
