import React from 'react';
import {
  Layers,
  CheckCircle2,
  AlertTriangle,
  Clock,
  DollarSign,
  Truck,
  Package,
  Calendar,
  ShieldCheck,
  Info,
} from 'lucide-react';
import OutcomeVarianceCards from './OutcomeVarianceCards';
import OutcomeStatusBadge from './OutcomeStatusBadge';

export default function PredictedActualComparison({ comparison, loading = false }) {
  if (loading) {
    return (
      <div className="p-8 text-center text-xs text-slate-400 space-y-2">
        <Clock className="h-5 w-5 animate-spin mx-auto text-red-400" />
        <p>Retrieving operational actuals and closed-loop comparison from PostgreSQL...</p>
      </div>
    );
  }

  if (!comparison) {
    return (
      <div className="p-6 text-center text-xs text-slate-400">
        No comparison data available.
      </div>
    );
  }

  const {
    decision_id,
    shipment_id,
    predicted = {},
    actual = {},
    variance = {},
    data_completeness = 'NO_OUTCOME',
    notes = [],
  } = comparison;

  const hasActual = actual != null && Object.keys(actual).length > 0;

  const formatCost = (val, currency = 'USD') => {
    if (val == null) return '—';
    return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString([], {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="space-y-5">
      {/* 1. Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h4 className="text-sm font-bold text-white tracking-tight">
                Closed-Loop Analytics: Predicted vs Actual Outcomes
              </h4>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-white/[0.06] text-slate-300 border border-white/[0.08]">
                {decision_id}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Empirical verification comparing prescriptive optimization models against real-world operations
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {hasActual ? (
            <OutcomeStatusBadge status={actual?.outcome_status || 'RECORDED'} />
          ) : (
            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">
              <Clock className="h-3 w-3" />
              <span>OUTCOME NOT RECORDED</span>
            </span>
          )}

          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
              data_completeness === 'COMPLETE'
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                : data_completeness === 'PARTIAL'
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
          >
            {data_completeness}
          </span>
        </div>
      </div>

      {/* 2. Variance Summary Cards */}
      {hasActual && (
        <OutcomeVarianceCards
          variance={variance}
          predicted={predicted}
          actual={actual}
        />
      )}

      {/* 3. Side-by-Side Comparison Table */}
      <div className="rounded-xl border border-white/[0.08] overflow-hidden bg-white/[0.01]">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/[0.06] text-slate-400 uppercase tracking-wider font-mono text-[10px] bg-white/[0.02]">
              <th className="py-3 px-4 font-semibold">Operational Dimension</th>
              <th className="py-3 px-4 font-semibold">Predicted Snapshot (At Execution)</th>
              <th className="py-3 px-4 font-semibold">Verified Operational Actual</th>
              <th className="py-3 px-4 font-semibold">Closed-Loop Variance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {/* Cost Row */}
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="py-3 px-4 font-semibold text-slate-200 flex items-center space-x-2">
                <DollarSign className="h-4 w-4 text-red-400" />
                <span>Total Cost</span>
              </td>
              <td className="py-3 px-4 font-mono font-bold text-slate-300">
                {formatCost(predicted?.predicted_cost, predicted?.currency)}
              </td>
              <td className="py-3 px-4 font-mono font-bold text-white">
                {hasActual && actual?.actual_cost != null
                  ? formatCost(actual.actual_cost, actual.currency)
                  : 'Pending invoice'}
              </td>
              <td className="py-3 px-4 font-mono">
                {variance?.cost_variance != null ? (
                  <span
                    className={`font-bold ${
                      variance.cost_variance > 0
                        ? 'text-amber-300'
                        : variance.cost_variance < 0
                        ? 'text-emerald-300'
                        : 'text-slate-300'
                    }`}
                  >
                    {variance.cost_variance > 0 ? '+' : ''}
                    ${variance.cost_variance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    {variance.cost_variance_percentage != null && (
                      <span className="text-[10px] ml-1 opacity-80">
                        ({variance.cost_variance_percentage > 0 ? '+' : ''}{variance.cost_variance_percentage}%)
                      </span>
                    )}
                  </span>
                ) : (
                  <span className="text-slate-500">—</span>
                )}
              </td>
            </tr>

            {/* Delivery Date Row */}
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="py-3 px-4 font-semibold text-slate-200 flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-red-400" />
                <span>Delivery Date</span>
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {formatDate(predicted?.predicted_delivery_date)}
              </td>
              <td className="py-3 px-4 font-mono text-white">
                {hasActual && actual?.actual_delivery_date
                  ? formatDate(actual.actual_delivery_date)
                  : 'Awaiting delivery'}
              </td>
              <td className="py-3 px-4 font-mono">
                {variance?.delivery_date_variance_days != null ? (
                  <span
                    className={`font-semibold ${
                      variance.delivery_date_variance_days > 0
                        ? 'text-amber-300'
                        : variance.delivery_date_variance_days < 0
                        ? 'text-emerald-300'
                        : 'text-slate-300'
                    }`}
                  >
                    {variance.delivery_date_variance_days > 0 ? '+' : ''}
                    {variance.delivery_date_variance_days} calendar days
                  </span>
                ) : (
                  <span className="text-slate-500">—</span>
                )}
              </td>
            </tr>

            {/* Delay Impact Row */}
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="py-3 px-4 font-semibold text-slate-200 flex items-center space-x-2">
                <Clock className="h-4 w-4 text-red-400" />
                <span>Schedule Delay</span>
              </td>
              <td className="py-3 px-4 font-mono text-red-300">
                {predicted?.predicted_delay != null
                  ? `${Number(predicted.predicted_delay).toFixed(1)} days delay`
                  : '—'}
              </td>
              <td className="py-3 px-4 font-mono text-white">
                {hasActual && actual?.actual_delay != null
                  ? `${Number(actual.actual_delay).toFixed(1)} days delay`
                  : 'Pending'}
              </td>
              <td className="py-3 px-4 font-mono">
                {variance?.delay_variance != null ? (
                  <span
                    className={`font-semibold ${
                      variance.delay_variance > 0
                        ? 'text-amber-300'
                        : variance.delay_variance < 0
                        ? 'text-emerald-300'
                        : 'text-slate-300'
                    }`}
                  >
                    {variance.delay_variance > 0 ? '+' : ''}
                    {Number(variance.delay_variance).toFixed(1)} days
                  </span>
                ) : (
                  <span className="text-slate-500">—</span>
                )}
              </td>
            </tr>

            {/* Supplier Row */}
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="py-3 px-4 font-semibold text-slate-200 flex items-center space-x-2">
                <Truck className="h-4 w-4 text-red-400" />
                <span>Fulfilling Supplier</span>
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {predicted?.planned_supplier || 'Assigned Carrier'}
              </td>
              <td className="py-3 px-4 font-mono text-white">
                {hasActual && actual?.actual_supplier
                  ? actual.actual_supplier
                  : 'Unconfirmed'}
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {variance?.supplier_matched != null ? (
                  variance.supplier_matched ? (
                    <span className="text-emerald-400 font-semibold flex items-center space-x-1">
                      <CheckCircle2 className="h-3 w-3 inline" />
                      <span>Planned Supplier</span>
                    </span>
                  ) : (
                    <span className="text-amber-300 font-semibold flex items-center space-x-1">
                      <AlertTriangle className="h-3 w-3 inline" />
                      <span>Substituted Supplier</span>
                    </span>
                  )
                ) : (
                  <span className="text-slate-500">—</span>
                )}
              </td>
            </tr>

            {/* Quantity Row */}
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="py-3 px-4 font-semibold text-slate-200 flex items-center space-x-2">
                <Package className="h-4 w-4 text-red-400" />
                <span>Order Quantity</span>
              </td>
              <td className="py-3 px-4 font-mono text-slate-300">
                {predicted?.planned_quantity != null
                  ? `${Number(predicted.planned_quantity).toLocaleString()} units`
                  : '—'}
              </td>
              <td className="py-3 px-4 font-mono text-white">
                {hasActual && actual?.actual_quantity != null
                  ? `${Number(actual.actual_quantity).toLocaleString()} units`
                  : 'Pending count'}
              </td>
              <td className="py-3 px-4 font-mono">
                {variance?.quantity_variance != null ? (
                  <span
                    className={`font-semibold ${
                      variance.quantity_variance === 0
                        ? 'text-slate-300'
                        : variance.quantity_variance < 0
                        ? 'text-amber-300'
                        : 'text-rose-300'
                    }`}
                  >
                    {variance.quantity_variance > 0 ? '+' : ''}
                    {Number(variance.quantity_variance).toLocaleString()} units
                  </span>
                ) : (
                  <span className="text-slate-500">—</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* 4. Notes & Explanations */}
      {notes && notes.length > 0 && (
        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-1.5 text-xs text-slate-400">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
            <Info className="h-3.5 w-3.5 text-red-400" />
            <span>Closed-Loop Variance Observations</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-slate-300 pl-1">
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 5. Data Governance Disclaimer */}
      <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 flex items-start space-x-2.5 text-xs text-slate-300">
        <ShieldCheck className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-slate-200">
            Day 19 Closed-Loop Audit Policy
          </div>
          <p className="text-[11px] text-slate-400 leading-normal">
            Operational actuals may be recorded via authorized operational integrations or manual invoice reconciliation.
            Predictions recorded at decision execution time remain immutable.
            {hasActual && actual?.source && (
              <span className="ml-1 text-red-300 font-mono">
                [Data Source: {actual.source}]
              </span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
