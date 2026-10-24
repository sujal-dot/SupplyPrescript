import React, { useState } from 'react';
import {
  X,
  FileCheck2,
  DollarSign,
  Calendar,
  Truck,
  Package,
  Layers,
  ShieldCheck,
  AlertCircle,
  Clock,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';
import { recordOutcome, formatApiError } from '../../services/decisionService';

export default function OutcomeEntryModal({
  isOpen,
  onClose,
  decision,
  onSuccess,
}) {
  const [actualCost, setActualCost] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [actualDeliveryDate, setActualDeliveryDate] = useState('');
  const [actualDelay, setActualDelay] = useState('');
  const [actualSupplier, setActualSupplier] = useState('');
  const [actualQuantity, setActualQuantity] = useState('');
  const [outcomeStatus, setOutcomeStatus] = useState('DELIVERED');
  const [source, setSource] = useState('manual_entry');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !decision) return null;

  const decisionId = decision.decision_id;
  const shipmentId = decision.shipment_id;
  const predCost = decision.predicted_cost ?? decision.estimated_total_cost;
  const predDelay = decision.predicted_delay;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const costNum = Number(actualCost);
    if (isNaN(costNum) || costNum < 0 || actualCost.trim() === '') {
      setError('A valid, non-negative actual cost is required.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        actual_cost: costNum,
        currency,
        actual_delivery_date: actualDeliveryDate.trim() || undefined,
        actual_delay: actualDelay.trim() !== '' ? Number(actualDelay) : undefined,
        actual_supplier: actualSupplier.trim() || undefined,
        actual_quantity: actualQuantity.trim() !== '' ? Number(actualQuantity) : undefined,
        outcome_status: outcomeStatus || (actualDeliveryDate ? 'DELIVERED' : 'RECORDED'),
        source,
        notes: notes.trim() || undefined,
      };

      const result = await recordOutcome(decisionId, payload);
      if (onSuccess) {
        onSuccess(result);
      }
      onClose();
    } catch (err) {
      setError(formatApiError(err) || 'Failed to record actual outcome.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="glass-card w-full max-w-xl rounded-[28px] border border-white/[0.16] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8),inset_0_1px_1.5px_rgba(255,255,255,0.35)] overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="outcome-modal-title"
      >
        {/* Header */}
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
              <FileCheck2 className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 id="outcome-modal-title" className="text-sm font-bold text-white tracking-tight">
                  Record Actual Operational Outcome
                </h3>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-red-500/15 text-red-300 border border-red-500/30">
                  {decisionId}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Target Shipment: <span className="text-white font-mono">{shipmentId}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form noValidate onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start space-x-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Reference Banner */}
          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] text-xs grid grid-cols-2 gap-2 text-slate-300 font-mono">
            <div>
              <span className="text-slate-500 block text-[10px]">Predicted Cost:</span>
              <span className="font-bold text-white">
                ${predCost != null ? Number(predCost).toLocaleString() : '—'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px]">Predicted Delay:</span>
              <span className="font-bold text-red-300">
                {predDelay != null ? `${Number(predDelay).toFixed(1)} days` : '—'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
            {/* Actual Cost */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Actual Cost ($) <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <DollarSign className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  placeholder="e.g. 16200.00"
                  value={actualCost}
                  onChange={(e) => setActualCost(e.target.value)}
                  className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg pl-9 pr-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
                />
              </div>
            </div>

            {/* Currency */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Currency
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
              >
                <option value="USD">USD (US Dollar)</option>
                <option value="EUR">EUR (Euro)</option>
                <option value="GBP">GBP (British Pound)</option>
                <option value="INR">INR (Indian Rupee)</option>
              </select>
            </div>

            {/* Actual Delivery Date */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Actual Delivery Date
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={actualDeliveryDate}
                  onChange={(e) => setActualDeliveryDate(e.target.value)}
                  className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
                />
              </div>
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                Leave empty if shipment is in-transit / awaiting delivery
              </span>
            </div>

            {/* Actual Delay Days */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Actual Delay Days (Optional)
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                placeholder="Auto-calculated if blank"
                value={actualDelay}
                onChange={(e) => setActualDelay(e.target.value)}
                className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                Auto-calculated from shipment baseline date
              </span>
            </div>

            {/* Actual Supplier */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Actual Fulfilling Supplier
              </label>
              <input
                type="text"
                placeholder="e.g. SUPPLIER_EXPEDITED"
                value={actualSupplier}
                onChange={(e) => setActualSupplier(e.target.value)}
                className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
              />
            </div>

            {/* Actual Quantity */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Delivered Quantity
              </label>
              <input
                type="number"
                step="1"
                min="1"
                placeholder="e.g. 1000"
                value={actualQuantity}
                onChange={(e) => setActualQuantity(e.target.value)}
                className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
              />
            </div>

            {/* Outcome Status */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Outcome Lifecycle Status
              </label>
              <select
                value={outcomeStatus}
                onChange={(e) => setOutcomeStatus(e.target.value)}
                className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
              >
                <option value="DELIVERED">DELIVERED (Final delivery received)</option>
                <option value="AWAITING_DELIVERY">AWAITING_DELIVERY (In transit)</option>
                <option value="RECORDED">RECORDED (Provisional)</option>
                <option value="CANCELLED">CANCELLED (Freight aborted)</option>
                <option value="DISPUTED">DISPUTED (Invoice discrepancy)</option>
              </select>
            </div>

            {/* Data Source */}
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
                Data Verification Source
              </label>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-red-500"
              >
                <option value="manual_entry">Manual Operational Entry</option>
                <option value="erp_invoice">ERP Vendor Invoice</option>
                <option value="carrier_webhook">Carrier Webhook (FedEx/DHL/Maersk)</option>
                <option value="warehouse_scan">Warehouse Inbound Scan</option>
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1 font-semibold">
              Operational Variance Notes &amp; Rationale
            </label>
            <textarea
              rows={2}
              placeholder="e.g. Fuel surcharge of $1,200 applied due to emergency weekend customs clearance."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-800 border border-white/[0.08] text-white rounded-lg p-2.5 text-xs focus:outline-none focus:border-red-500"
            />
          </div>

          {/* Governance Notice */}
          <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/80 flex items-start space-x-2 text-xs text-slate-400">
            <ShieldCheck className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-[11px] leading-normal">
              Submitting this form persists an immutable outcome in PostgreSQL and locks the decision to one final outcome.
              Original predictions recorded at decision execution time remain unmodified.
            </p>
          </div>

          {/* Buttons */}
          <div className="pt-2 flex items-center justify-end space-x-2.5">
            <GlassButton variant="outline" size="sm" onClick={onClose} disabled={loading} type="button">
              Cancel
            </GlassButton>
            <GlassButton variant="primary" size="sm" loading={loading} type="submit">
              Commit Actual Outcome
            </GlassButton>
          </div>
        </form>
      </div>
    </div>
  );
}
