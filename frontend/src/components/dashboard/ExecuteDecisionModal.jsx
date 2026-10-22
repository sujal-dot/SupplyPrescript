import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldCheck,
  AlertTriangle,
  Send,
  Sparkles,
  Plane,
  Building2,
  CalendarClock,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  DollarSign,
  Layers,
  Info,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';

export default function ExecuteDecisionModal({
  option = null,
  shipment = null,
  baseline = null,
  isOpen = false,
  onClose,
  onConfirmExecution,
  loading = false,
  error = null,
}) {
  const [notes, setNotes] = useState('');
  const [approvedBy, setApprovedBy] = useState('Operations Manager');
  const [localError, setLocalError] = useState(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setNotes('');
      setApprovedBy('Operations Manager');
      setLocalError(null);
    }
  }, [isOpen, option]);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen && !loading) {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, loading, onClose]);

  if (!isOpen || !option) return null;

  const targetShipmentId = shipment?.shipment_id || option.shipment_id || 'N/A';
  const optionId = option.option_id || 'A';
  const strategyName = option.name || option.strategy || `Option ${optionId}`;
  const strategyCode = option.strategy || (optionId === 'A' ? 'AIR_FREIGHT' : optionId === 'B' ? 'SECONDARY_SUPPLIER' : 'DELAY_LAUNCH');

  const resolvedFeasibility = (option.status || option.feasibility || 'FEASIBLE').toUpperCase();
  const isFeasible = resolvedFeasibility === 'FEASIBLE';

  const formatCost = (val) => {
    if (val == null) return '—';
    return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDelta = (val, pct) => {
    if (val == null) return null;
    const num = Number(val);
    const sign = num > 0 ? '+' : '';
    const pctStr = pct != null ? ` (${sign}${Number(pct).toFixed(1)}%)` : '';
    return `${sign}$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${pctStr}`;
  };

  const getStrategyIcon = () => {
    if (strategyCode === 'AIR_FREIGHT' || optionId === 'A') return Plane;
    if (strategyCode === 'SECONDARY_SUPPLIER' || optionId === 'B') return Building2;
    return CalendarClock;
  };
  const StrategyIcon = getStrategyIcon();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isFeasible) {
      setLocalError('Cannot execute an infeasible option violating hard constraints.');
      return;
    }

    // Generate unique client-side idempotency key for network retry safety
    const idempotencyKey = `exec-${targetShipmentId}-${optionId}-${Date.now()}`;

    onConfirmExecution?.({
      shipment_id: targetShipmentId,
      option_id: optionId,
      strategy: strategyCode,
      optimization_run_id: option.optimization_run_id || undefined,
      idempotency_key: idempotencyKey,
      notes: notes.trim() || undefined,
      approved_by: approvedBy.trim() || 'Operations Manager',
    });
  };

  const displayError = localError || error;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="glass-card w-full max-w-xl max-h-[90vh] rounded-3xl border border-white/[0.12] bg-[#0c1626]/95 flex flex-col shadow-2xl shadow-cyan-950/60 overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-white/[0.08] flex items-start justify-between bg-white/[0.02]">
          <div className="flex items-center space-x-3.5">
            <div className="p-3 rounded-2xl bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 shadow-lg shadow-cyan-500/10">
              <StrategyIcon className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-300 font-bold bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-400/20">
                  Option {optionId}
                </span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                  {strategyCode}
                </span>
              </div>
              <h2 id="modal-title" className="text-xl font-bold text-white tracking-tight mt-1">
                Confirm &amp; Execute Decision
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={loading}
            aria-label="Close modal"
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">
          {/* Error Banner */}
          {displayError && (
            <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-start space-x-2.5 text-rose-300">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
              <div className="space-y-0.5">
                <strong className="font-bold block">Execution Blocked</strong>
                <span>{typeof displayError === 'string' ? displayError : JSON.stringify(displayError)}</span>
              </div>
            </div>
          )}

          {/* Target Shipment & Strategy Banner */}
          <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.08] space-y-3">
            <div className="flex items-center justify-between border-b border-white/[0.05] pb-2.5">
              <span className="text-slate-400 font-medium">Target Shipment</span>
              <span className="font-mono font-bold text-white text-sm bg-white/[0.06] px-2.5 py-0.5 rounded-md border border-white/[0.08]">
                {targetShipmentId}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium">Selected Alternative</span>
              <span className="font-mono font-bold text-cyan-300">
                Option {optionId}: {strategyName}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium">Strategic Action</span>
              <span className="text-slate-200">
                {option.explanation || 'Prescriptive mixed-integer optimization recommendation.'}
              </span>
            </div>
          </div>

          {/* Authoritative Financial & Delivery Metrics */}
          <div className="grid grid-cols-2 gap-3.5">
            {/* Estimated Total Cost */}
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Estimated Total Cost
              </span>
              <span className="text-lg font-bold font-mono text-white block">
                {formatCost(option.estimated_total_cost)}
              </span>
              {option.additional_cost != null && (
                <span
                  className={`text-[11px] font-mono block ${
                    Number(option.additional_cost) > 0
                      ? 'text-rose-400'
                      : Number(option.additional_cost) < 0
                      ? 'text-emerald-400'
                      : 'text-slate-400'
                  }`}
                >
                  {formatDelta(option.additional_cost, option.additional_cost_percentage)} vs baseline
                </span>
              )}
            </div>

            {/* Estimated Delivery Time */}
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Expected Delivery
              </span>
              <span className="text-lg font-bold font-mono text-cyan-300 block">
                {option.estimated_delivery_days != null
                  ? `${Number(option.estimated_delivery_days).toFixed(1)} days`
                  : '—'}
              </span>
              {option.schedule_impact_days != null && (
                <span className="text-[11px] font-mono text-slate-400 block">
                  {Number(option.schedule_impact_days) <= 0
                    ? `${Math.abs(Number(option.schedule_impact_days)).toFixed(1)}d faster`
                    : `+${Number(option.schedule_impact_days).toFixed(1)}d delay`}
                </span>
              )}
            </div>
          </div>

          {/* Operational Risk & Constraint Audit */}
          <div className="p-3.5 rounded-xl bg-black/25 border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400">Delay Risk Level:</span>
              <span className="font-mono font-bold text-slate-200">
                {option.risk_level || 'LOW'}{' '}
                {option.delay_probability != null &&
                  `(${Math.round(Number(option.delay_probability) * 100)}% probability)`}
              </span>
            </div>

            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-white/[0.04]">
              <span className="text-slate-400">Day 15 Budget Ceiling Check:</span>
              <span
                className={`font-mono font-bold flex items-center space-x-1 ${
                  (option.constraint_violations || []).some((v) =>
                    v.constraint_name.toLowerCase().includes('budget')
                  )
                    ? 'text-rose-400'
                    : isFeasible
                    ? 'text-emerald-400'
                    : 'text-slate-400'
                }`}
              >
                {(option.constraint_violations || []).some((v) =>
                  v.constraint_name.toLowerCase().includes('budget')
                ) ? (
                  <>
                    <XCircle className="h-3.5 w-3.5 inline" />
                    <span>FAIL</span>
                  </>
                ) : isFeasible ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 inline" />
                    <span>PASS ($50,000 ceiling enforced)</span>
                  </>
                ) : (
                  <span>UNVERIFIED</span>
                )}
              </span>
            </div>

            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400">Capacity &amp; Safety SLA Check:</span>
              <span
                className={`font-mono font-bold flex items-center space-x-1 ${
                  (option.constraint_violations || []).some(
                    (v) =>
                      v.constraint_name.toLowerCase().includes('capacity') ||
                      v.constraint_name.toLowerCase().includes('delivery')
                  )
                    ? 'text-rose-400'
                    : isFeasible
                    ? 'text-emerald-400'
                    : 'text-slate-400'
                }`}
              >
                {(option.constraint_violations || []).some(
                  (v) =>
                    v.constraint_name.toLowerCase().includes('capacity') ||
                    v.constraint_name.toLowerCase().includes('delivery')
                ) ? (
                  <>
                    <XCircle className="h-3.5 w-3.5 inline" />
                    <span>FAIL</span>
                  </>
                ) : isFeasible ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 inline" />
                    <span>PASS</span>
                  </>
                ) : (
                  <span>UNVERIFIED</span>
                )}
              </span>
            </div>
          </div>

          {/* Key Model Assumptions */}
          {option.assumptions && option.assumptions.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block font-bold flex items-center space-x-1">
                <Layers className="h-3 w-3 text-cyan-400" />
                <span>Model Assumptions &amp; Prerequisites</span>
              </span>
              <ul className="list-disc list-inside space-y-1 text-slate-400 bg-white/[0.02] p-3 rounded-xl border border-white/[0.04] text-[11px]">
                {option.assumptions.map((asm, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {asm}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Operational Governance Notice: No Automated External Booking */}
          <div className="p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-slate-300 space-y-1.5 text-[11px] leading-relaxed">
            <div className="flex items-center space-x-1.5 text-cyan-300 font-bold">
              <ShieldCheck className="h-4 w-4 text-cyan-400 shrink-0" />
              <span>Safe Operational Protocol (No Automated External Booking)</span>
            </div>
            <p>
              Confirming this action records the authorized prescriptive decision in SupplyPrescript with status{' '}
              <strong className="text-cyan-200 font-mono">RECORDED</strong>. In accordance with system safety boundaries, this action{' '}
              <strong className="text-white">does NOT automatically disburse funds, charge accounts, or dispatch physical carriers</strong>.
              The external execution status will be set to{' '}
              <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-600 font-mono text-[10px] text-cyan-300 font-bold">
                NOT_EXECUTED
              </span>{' '}
              pending dispatch coordination.
            </p>
          </div>

          {/* Execution Form Controls */}
          <form id="execute-decision-form" onSubmit={handleSubmit} className="space-y-3.5 pt-1">
            {/* Authorizing Authority */}
            <div className="space-y-1">
              <label htmlFor="approvedByInput" className="text-[10px] font-mono uppercase tracking-wider text-slate-300 block font-bold">
                Authorizing Authority
              </label>
              <input
                id="approvedByInput"
                type="text"
                value={approvedBy}
                onChange={(e) => setApprovedBy(e.target.value)}
                disabled={loading}
                className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-cyan-400/40 rounded-xl px-3 py-2 text-xs text-white focus:outline-none transition-colors"
                required
              />
            </div>

            {/* Operational Notes */}
            <div className="space-y-1">
              <label htmlFor="notesInput" className="text-[10px] font-mono uppercase tracking-wider text-slate-300 block font-bold">
                Operational Notes &amp; Context (Optional)
              </label>
              <textarea
                id="notesInput"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={loading}
                placeholder="e.g. Authorized expedited transit to mitigate tier-1 customer line-down penalty."
                className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-cyan-400/40 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none resize-none transition-colors"
              />
            </div>
          </form>
        </div>

        {/* Modal Footer */}
        <div className="p-5 border-t border-white/[0.08] bg-white/[0.02] flex items-center justify-end space-x-3">
          <GlassButton
            type="button"
            variant="secondary"
            size="sm"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </GlassButton>
          <GlassButton
            type="submit"
            form="execute-decision-form"
            variant="primary"
            size="sm"
            icon={Sparkles}
            loading={loading}
            disabled={!isFeasible || loading}
          >
            Confirm &amp; Execute Decision
          </GlassButton>
        </div>
      </div>
    </div>
  );
}
