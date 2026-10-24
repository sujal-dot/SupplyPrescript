import React from 'react';
import {
  Package,
  Building2,
  MapPin,
  Calendar,
  DollarSign,
  Truck,
  Clock,
  Sparkles,
} from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';

export default function ShipmentSummary({ baseline = null, shipment = null }) {
  if (!baseline && !shipment) return null;

  const data = baseline || shipment;

  const shipmentId = data.shipment_id || 'N/A';
  const productName = data.product_name || data.product_id || 'Industrial SKU';
  const supplierName = data.supplier_name || data.supplier_id || 'Primary Supplier';
  const origin = data.origin || 'Mumbai';
  const destination = data.destination || 'Delhi';
  const quantity = data.quantity ? Number(data.quantity).toLocaleString() : '—';
  const unitCost = data.unit_cost != null ? `$${Number(data.unit_cost).toFixed(2)}` : '—';
  const shippingCost = data.shipping_cost != null ? `$${Number(data.shipping_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—';
  const totalCost = data.estimated_total_cost != null ? `$${Number(data.estimated_total_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—';
  const leadTime = data.planned_lead_time_days ?? data.lead_time ?? '—';
  const delayDays = data.predicted_delay_days ?? data.delay_days ?? 0;
  const transportMode = data.transport_mode || 'Road';
  const riskLevel = data.risk_level || 'LOW';

  return (
    <div className="glass-card p-5 rounded-2xl border border-white/[0.08] bg-white/[0.02]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <Package className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold text-red-300">{shipmentId}</span>
              <StatusBadge status={riskLevel} />
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight mt-0.5">{productName}</h3>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <span className="flex items-center space-x-1">
            <Building2 className="h-3.5 w-3.5 text-slate-500" />
            <strong className="text-slate-200">{supplierName}</strong>
          </span>
          <span>•</span>
          <span className="flex items-center space-x-1">
            <MapPin className="h-3.5 w-3.5 text-slate-500" />
            <span>{origin} → {destination}</span>
          </span>
        </div>
      </div>

      {/* Baseline Metric Matrix */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-3 text-xs">
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">Quantity</span>
          <span className="font-semibold text-slate-200 font-mono">{quantity} units</span>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">Unit Price</span>
          <span className="font-semibold text-slate-200 font-mono">{unitCost}</span>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">Base Freight</span>
          <span className="font-semibold text-slate-200 font-mono">{shippingCost}</span>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">Base Expenditure</span>
          <span className="font-semibold text-red-300 font-mono font-bold">{totalCost}</span>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">Modal Transit</span>
          <span className="font-semibold text-slate-200">{leadTime} d ({transportMode})</span>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">Baseline Delay</span>
          <span className={`font-semibold font-mono ${Number(delayDays) > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            +{Number(delayDays).toFixed(1)} days
          </span>
        </div>
      </div>
    </div>
  );
}
