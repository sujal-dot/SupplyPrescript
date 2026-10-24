import React from 'react';
import { DollarSign, Clock, Calendar, Package, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export default function DecisionROITable({ roiData = {}, comparison = null }) {
  const { cost = {}, delivery = {}, currency = 'USD' } = roiData;

  const formatCost = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatCostDiff = (val, pct) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    const pctStr = pct != null ? ` (${pct > 0 ? '+' : ''}${pct}%)` : '';
    return `${sign}$${Math.abs(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${pctStr}`;
  };

  const formatDays = (val) => {
    if (val == null) return '—';
    return `${Number(val).toFixed(1)} days`;
  };

  const formatDaysDiff = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}${Math.abs(num).toFixed(1)} days`;
  };

  // Derive extra comparison metrics if passed from outcome comparison
  const predDeliveryDate = comparison?.predicted?.predicted_delivery_date;
  const actDeliveryDate = comparison?.actual?.actual_delivery_date;
  const dateVarianceDays = comparison?.variance?.delivery_date_variance_days;

  const plannedQty = comparison?.predicted?.planned_quantity;
  const actQty = comparison?.actual?.actual_quantity;
  const qtyVariance = comparison?.variance?.quantity_variance;

  const rows = [];

  // 1. Cost row
  if (cost.predicted_cost != null || cost.actual_cost != null) {
    const diff = cost.cost_difference != null ? Number(cost.cost_difference) : null;
    rows.push({
      key: 'cost',
      label: 'Financial Cost',
      icon: DollarSign,
      predicted: cost.predicted_cost != null ? `${formatCost(cost.predicted_cost)} ${currency}` : '—',
      actual: cost.actual_cost != null ? `${formatCost(cost.actual_cost)} ${currency}` : 'Pending actuals',
      difference: formatCostDiff(cost.cost_difference, cost.cost_variance_percentage),
      diffClass: diff != null ? (diff > 0 ? 'text-amber-300' : diff < 0 ? 'text-emerald-300' : 'text-slate-300') : 'text-slate-500',
    });
  }

  // 2. Delay row
  if (delivery.predicted_delay != null || delivery.actual_delay != null) {
    const diff = delivery.delay_difference != null ? Number(delivery.delay_difference) : null;
    rows.push({
      key: 'delay',
      label: 'Delay Impact',
      icon: Clock,
      predicted: delivery.predicted_delay != null ? formatDays(delivery.predicted_delay) : '—',
      actual: delivery.actual_delay != null ? formatDays(delivery.actual_delay) : 'Pending delivery',
      difference: formatDaysDiff(delivery.delay_difference),
      diffClass: diff != null ? (diff > 0 ? 'text-amber-300' : diff < 0 ? 'text-emerald-300' : 'text-slate-300') : 'text-slate-500',
    });
  }

  // 3. Delivery Date row (if supported)
  if (predDeliveryDate || actDeliveryDate) {
    const diff = dateVarianceDays != null ? Number(dateVarianceDays) : null;
    rows.push({
      key: 'date',
      label: 'Delivery Date',
      icon: Calendar,
      predicted: predDeliveryDate ? new Date(predDeliveryDate).toLocaleDateString() : '—',
      actual: actDeliveryDate ? new Date(actDeliveryDate).toLocaleDateString() : 'Pending delivery',
      difference: diff != null ? `${diff > 0 ? '+' : ''}${diff} calendar days` : '—',
      diffClass: diff != null ? (diff > 0 ? 'text-amber-300' : diff < 0 ? 'text-emerald-300' : 'text-slate-300') : 'text-slate-500',
    });
  }

  // 4. Quantity row (if supported)
  if (plannedQty != null || actQty != null) {
    const diff = qtyVariance != null ? Number(qtyVariance) : null;
    rows.push({
      key: 'quantity',
      label: 'Quantity Delivered',
      icon: Package,
      predicted: plannedQty != null ? `${Number(plannedQty).toLocaleString()} units` : '—',
      actual: actQty != null ? `${Number(actQty).toLocaleString()} units` : 'Pending fulfillment',
      difference: diff != null ? `${diff > 0 ? '+' : ''}${diff.toLocaleString()} units` : '—',
      diffClass: diff != null ? (diff < 0 ? 'text-amber-300' : diff > 0 ? 'text-emerald-300' : 'text-slate-300') : 'text-slate-500',
    });
  }

  if (rows.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-white/[0.06] overflow-hidden bg-white/[0.01]">
      <div className="px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between">
        <span className="text-[11px] font-mono font-bold text-slate-300 uppercase tracking-wider">
          Decision Detail Comparison
        </span>
        <span className="text-[10px] text-slate-500 font-mono">
          Only displaying parameters supported by persisted records
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-white/[0.06] text-slate-400 text-[10px] uppercase bg-white/[0.02]">
              <th className="py-2.5 px-4 font-semibold">Metric</th>
              <th className="py-2.5 px-4 font-semibold text-right">Predicted (Snapshot)</th>
              <th className="py-2.5 px-4 font-semibold text-right">Actual (Outcome)</th>
              <th className="py-2.5 px-4 font-semibold text-right">Difference (Variance)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {rows.map((r) => {
              const Icon = r.icon;
              return (
                <tr key={r.key} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-2.5 px-4 text-slate-200 flex items-center space-x-2">
                    <Icon className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                    <span>{r.label}</span>
                  </td>
                  <td className="py-2.5 px-4 text-right text-slate-300">{r.predicted}</td>
                  <td className="py-2.5 px-4 text-right text-slate-200 font-bold">{r.actual}</td>
                  <td className={`py-2.5 px-4 text-right font-bold ${r.diffClass}`}>
                    {r.difference}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
