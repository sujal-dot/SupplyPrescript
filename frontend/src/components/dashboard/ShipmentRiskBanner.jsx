import React from 'react';
import {
  AlertTriangle,
  Sparkles,
  Truck,
  Building2,
  Calendar,
  Clock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';
import StatusBadge from '../ui/StatusBadge';

export default function ShipmentRiskBanner({
  shipment = null,
  loading = false,
  onEvaluateAlternatives,
  onInspectShipment,
}) {
  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] animate-pulse flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-4 w-48 bg-white/[0.06] rounded" />
          <div className="h-6 w-72 bg-white/[0.08] rounded" />
        </div>
        <div className="h-9 w-40 bg-white/[0.06] rounded-xl" />
      </div>
    );
  }

  // Meaningful empty state if no high-risk shipment exists
  if (!shipment) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="h-6 w-6 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-emerald-300">
                Network Status Nominal
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-bold">
                Zero High Risk
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              No critical delay risks detected across active shipments in the database.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const {
    shipment_id,
    product_name,
    product_id,
    supplier_name,
    supplier_id,
    predicted_delay_days,
    delay_days,
    delay_probability,
    risk_level,
    expected_delivery_date,
    transport_mode,
  } = shipment;

  const displayDelay = predicted_delay_days != null ? Number(predicted_delay_days) : (delay_days != null ? Number(delay_days) : 0);
  const displayProb = delay_probability != null ? Math.round(Number(delay_probability) * 100) : null;
  const displayRisk = (risk_level || (displayProb && displayProb >= 70 ? 'HIGH' : 'MEDIUM')).toUpperCase();

  return (
    <div className="glass-card p-6 rounded-2xl border border-rose-500/30 bg-gradient-to-r from-rose-500/10 via-slate-900/60 to-transparent relative overflow-hidden shadow-xl shadow-rose-950/20">
      {/* Background Accent Glow */}
      <div className="absolute -right-16 -top-16 w-64 h-64 rounded-full bg-rose-500/10 blur-[80px] pointer-events-none" />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
        {/* Left Column: Shipment & Product Details */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30">
              <AlertTriangle className="h-4 w-4" />
            </div>
            <span className="text-[11px] font-mono tracking-wider text-rose-300 uppercase font-bold">
              High-Risk Shipment Flagged
            </span>
            <StatusBadge status={displayRisk} variant="error" />
          </div>

          <div>
            <div className="flex items-baseline space-x-3">
              <h2 className="text-xl font-bold text-white tracking-tight">
                {product_name || product_id || 'Industrial SKU'}
              </h2>
              <span className="text-xs font-mono text-red-300 font-bold bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.08]">
                {shipment_id}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 mt-1.5">
              <span className="flex items-center space-x-1">
                <Building2 className="h-3.5 w-3.5 text-slate-500" />
                <span>Supplier: <strong className="text-slate-200">{supplier_name || supplier_id || 'N/A'}</strong></span>
              </span>
              {transport_mode && (
                <span className="flex items-center space-x-1">
                  <Truck className="h-3.5 w-3.5 text-slate-500" />
                  <span>Mode: <strong className="text-slate-200">{transport_mode}</strong></span>
                </span>
              )}
              {expected_delivery_date && (
                <span className="flex items-center space-x-1">
                  <Calendar className="h-3.5 w-3.5 text-slate-500" />
                  <span>Due: <strong className="text-slate-200">{expected_delivery_date}</strong></span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Center/Right Metrics & Actions */}
        <div className="flex flex-wrap items-center gap-6 lg:border-l lg:border-white/[0.08] lg:pl-6">
          {/* Predicted Delay */}
          <div className="text-left">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
              Predicted Delay
            </span>
            <div className="flex items-baseline space-x-1.5 mt-0.5">
              <span className="text-2xl font-bold text-rose-400 font-mono">
                +{displayDelay.toFixed(1)}
              </span>
              <span className="text-xs text-rose-300 font-semibold">days</span>
            </div>
          </div>

          {/* Delay Probability */}
          {displayProb !== null && (
            <div className="text-left">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
                Delay Probability
              </span>
              <div className="flex items-baseline space-x-1 mt-0.5">
                <span className="text-2xl font-bold text-amber-300 font-mono">
                  {displayProb}%
                </span>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center space-x-2.5 w-full sm:w-auto">
            {onInspectShipment && (
              <GlassButton
                variant="secondary"
                size="md"
                onClick={() => onInspectShipment(shipment)}
              >
                View Shipment
              </GlassButton>
            )}
            <GlassButton
              variant="primary"
              size="md"
              icon={Sparkles}
              onClick={() => onEvaluateAlternatives?.(shipment.shipment_id)}
            >
              Generate Recommendations
            </GlassButton>
          </div>
        </div>
      </div>
    </div>
  );
}
