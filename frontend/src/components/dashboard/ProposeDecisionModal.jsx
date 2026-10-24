import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  ShieldCheck,
  AlertTriangle,
  Send,
  Sparkles,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';

export default function ProposeDecisionModal({
  option = null,
  shipment = null,
  isOpen = false,
  onClose,
  onSubmitProposal,
  loading = false,
}) {
  const [notes, setNotes] = useState('');
  const [operatorRole, setOperatorRole] = useState('Logistics Operations Manager');

  if (!isOpen || !option) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmitProposal?.({
      shipment_id: shipment?.shipment_id || option.shipment_id,
      option_id: option.option_id,
      option_name: option.name || option.strategy,
      decision_reason: option.explanation || 'Approved prescriptive optimization alternative.',
      notes: notes.trim(),
      proposed_by: operatorRole,
    });
  };

  const formatCost = (val) => {
    if (val == null) return '—';
    return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-card w-full max-w-lg rounded-[28px] border border-white/[0.16] flex flex-col shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8),inset_0_1px_1.5px_rgba(255,255,255,0.35)] overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-white/[0.08] flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-2xl bg-red-500/20 text-red-300 border border-red-500/30">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Propose Strategic Decision
              </h2>
              <p className="text-xs text-slate-400">
                SupplyPrescript Prescriptive Governance Workflow
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={loading}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {/* Target Summary */}
          <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Target Shipment:</span>
              <span className="font-mono font-bold text-white">
                {shipment?.shipment_id || 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Selected Alternative:</span>
              <span className="font-mono font-bold text-red-300">
                Option {option.option_id}: {option.name || option.strategy}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Estimated Total Expenditure:</span>
              <span className="font-mono font-bold text-slate-200">
                {formatCost(option.estimated_total_cost)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Expected Delivery Duration:</span>
              <span className="font-mono font-bold text-slate-200">
                {option.estimated_delivery_days != null ? `${Number(option.estimated_delivery_days).toFixed(1)} days` : '—'}
              </span>
            </div>
          </div>

          {/* Governance Notice */}
          <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-slate-300 space-y-1 text-[11px] leading-relaxed">
            <strong className="text-red-300 flex items-center space-x-1 font-bold">
              <ShieldCheck className="h-3.5 w-3.5 text-red-400" />
              <span>Safe Governance Protocol</span>
            </strong>
            <p>
              Submitting this proposal creates a record in the database with status{' '}
              <strong className="text-red-200 font-mono">PENDING</strong>. It does not disburse company funds or trigger automated carrier dispatch without managerial approval.
            </p>
          </div>

          {/* Operator Role */}
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-slate-300 font-mono uppercase tracking-wider block">
              Submitting Authority
            </label>
            <input
              type="text"
              value={operatorRole}
              onChange={(e) => setOperatorRole(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-red-500/40 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
              required
            />
          </div>

          {/* Operational Notes */}
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-slate-300 font-mono uppercase tracking-wider block">
              Operational Notes &amp; Context (Optional)
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Approved expedite for priority customer order; verified secondary supplier capacity."
              className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-red-500/40 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none resize-none"
            />
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-white/[0.08] flex items-center justify-end space-x-2.5">
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
              variant="primary"
              size="sm"
              icon={Send}
              loading={loading}
            >
              Submit Proposed Decision
            </GlassButton>
          </div>
        </form>
      </div>
    </div>
  );
}
