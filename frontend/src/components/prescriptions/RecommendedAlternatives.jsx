import React from 'react';
import {
  Sparkles,
  Plane,
  Building2,
  CalendarClock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  TrendingUp,
  DollarSign,
  Clock,
  Shield,
  Layers,
  ArrowRight,
  Info,
  Check,
} from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';
import GlassCard from '../ui/GlassCard';

export default function RecommendedAlternatives({
  data,
  loading = false,
  error = null,
  onSelectOption = null,
}) {
  if (loading) {
    return (
      <div className="glass-card p-8 rounded-2xl border border-white/[0.08] text-center flex flex-col items-center justify-center min-h-[360px] animate-pulse">
        <div className="p-4 rounded-2xl bg-red-500/10 text-red-400 border border-red-500/20 mb-4">
          <Sparkles className="h-8 w-8 animate-spin text-red-400" />
        </div>
        <h3 className="text-base font-bold text-white tracking-tight">
          Solving Prescriptive Optimization Engine
        </h3>
        <p className="text-xs text-slate-400 mt-2 max-w-md">
          Evaluating mathematical programming alternatives: computing dynamic air modal rates, verifying secondary supplier capacities, scoring active XGBoost delay models, and auditing hard budget constraints...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-rose-500/30 bg-rose-500/5">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-bold text-rose-300">
              Prescriptive Decision Error
            </h4>
            <p className="text-xs text-slate-300 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="glass-card p-8 rounded-2xl border border-white/[0.08] text-center flex flex-col items-center justify-center min-h-[280px]">
        <div className="p-4 rounded-2xl bg-white/[0.04] text-slate-400 border border-white/[0.08] mb-3">
          <Layers className="h-8 w-8 text-red-400/70" />
        </div>
        <h3 className="text-base font-bold text-white tracking-tight">
          Awaiting Shipment Selection
        </h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md">
          Select or predict an at-risk shipment to trigger the Day 13 prescriptive engine and generate three actionable decision alternatives.
        </p>
      </div>
    );
  }

  const {
    shipment_id,
    baseline,
    alternatives = [],
    recommended_option_id,
    recommendation_status,
    recommendation_reason,
    trade_off_analysis,
    warnings = [],
    model_version = 'v1.0',
    evaluated_at,
  } = data;

  const optA = alternatives.find((o) => o.option_id === 'A') || alternatives[0];
  const optB = alternatives.find((o) => o.option_id === 'B') || alternatives[1];
  const optC = alternatives.find((o) => o.option_id === 'C') || alternatives[2];

  const getFeasibilityBadge = (feasibility) => {
    switch (feasibility) {
      case 'FEASIBLE':
        return { variant: 'success', label: 'Feasible (Verified)', icon: CheckCircle2 };
      case 'INFEASIBLE':
        return { variant: 'error', label: 'Infeasible (Violations)', icon: XCircle };
      case 'INSUFFICIENT_DATA':
        return { variant: 'warning', label: 'Insufficient Data', icon: HelpCircle };
      default:
        return { variant: 'neutral', label: feasibility || 'Error', icon: AlertTriangle };
    }
  };

  const formatCost = (val) =>
    val != null && !isNaN(val) ? `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Not Configured';

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-white/[0.08] gap-2">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Recommended Alternative Decisions
            </h2>
            <p className="text-xs text-slate-400">
              Evaluated for Shipment <span className="font-mono text-red-300 font-semibold">{shipment_id}</span> ({baseline?.product_name || 'Product'})
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
          <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08]">
            Model {model_version}
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08]">
            Baseline Lead: {baseline?.planned_lead_time_days || 0}d
          </span>
        </div>
      </div>

      {/* Winning Prescriptive Recommendation Banner */}
      {recommended_option_id ? (
        <div className="p-5 rounded-2xl border border-emerald-500/40 bg-gradient-to-r from-emerald-500/15 via-emerald-500/5 to-transparent relative overflow-hidden">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
                <Check className="h-5 w-5 font-bold" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
                    Optimal Prescriptive Action
                  </span>
                  <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Option {recommended_option_id}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mt-1">
                  {recommendation_reason || `Option ${recommended_option_id} is recommended.`}
                </h3>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-5 rounded-2xl border border-amber-500/40 bg-gradient-to-r from-amber-500/15 via-amber-500/5 to-transparent">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400">
                Safety Gate Audit Notice
              </span>
              <h3 className="text-sm font-bold text-white mt-1">
                {recommendation_reason || 'No candidate alternative satisfies all mandatory business constraints (NO_FEASIBLE_OPTION).'}
              </h3>
            </div>
          </div>
        </div>
      )}

      {/* Three Comparison Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card A: Air Freight */}
        {optA && (
          <div
            className={`glass-card p-5 rounded-2xl border transition-all duration-300 flex flex-col justify-between ${
              optA.is_recommended
                ? 'border-emerald-500/50 bg-emerald-500/[0.04] shadow-[0_0_25px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/30'
                : optA.feasibility === 'INFEASIBLE'
                ? 'border-rose-500/30 bg-rose-500/[0.02]'
                : 'border-white/[0.08] hover:border-white/[0.16]'
            }`}
          >
            <div>
              {/* Card Header */}
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                <div className="flex items-center space-x-2">
                  <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
                    <Plane className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="text-xs font-mono font-bold text-red-400 uppercase tracking-wider">
                      Option A
                    </span>
                    <h4 className="text-sm font-bold text-white leading-tight">
                      Air Freight Expedited
                    </h4>
                  </div>
                </div>
                {(() => {
                  const badge = getFeasibilityBadge(optA.feasibility);
                  return <StatusBadge status={badge.label} variant={badge.variant} dot={true} />;
                })()}
              </div>

              {/* Metrics */}
              <div className="py-4 space-y-3">
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <div className="text-[11px] text-slate-400 font-mono">Estimated Total Cost</div>
                  <div className="flex items-baseline space-x-2 mt-0.5">
                    <span className="text-xl font-mono font-extrabold text-white">
                      {formatCost(optA.estimated_total_cost)}
                    </span>
                    {optA.additional_cost != null && (
                      <span className="text-xs font-mono text-red-300">
                        ({optA.additional_cost_percentage >= 0 ? '+' : ''}{optA.additional_cost_percentage}%)
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 font-mono">
                    Freight delta: {optA.additional_cost != null ? `+$${optA.additional_cost.toLocaleString()}` : 'N/A'}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] text-slate-500 block">Est. Delivery</span>
                    <span className="text-sm font-bold text-white">
                      {optA.estimated_delivery_days != null ? `${optA.estimated_delivery_days.toFixed(1)} days` : 'N/A'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] text-slate-500 block">Delay Risk</span>
                    <span className={`text-sm font-bold ${optA.risk_level === 'LOW' ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {optA.delay_probability != null ? `${Math.round(optA.delay_probability * 100)}% (${optA.risk_level})` : 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Constraint Violations if any */}
                {optA.constraint_violations?.length > 0 && (
                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300 space-y-1">
                    <span className="font-bold block">Constraint Violations:</span>
                    {optA.constraint_violations.map((v, i) => (
                      <div key={i}>• {v.message}</div>
                    ))}
                  </div>
                )}

                {/* Benefits / Trade-offs */}
                <div className="text-xs text-slate-300 leading-relaxed pt-1">
                  {optA.explanation}
                </div>
              </div>
            </div>

            {optA.is_recommended && (
              <div className="mt-2 pt-3 border-t border-emerald-500/20 text-center text-xs font-mono font-bold text-emerald-400">
                ★ Prescribed Choice
              </div>
            )}
          </div>
        )}

        {/* Card B: Secondary Supplier */}
        {optB && (
          <div
            className={`glass-card p-5 rounded-2xl border transition-all duration-300 flex flex-col justify-between ${
              optB.is_recommended
                ? 'border-emerald-500/50 bg-emerald-500/[0.04] shadow-[0_0_25px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/30'
                : optB.feasibility === 'INFEASIBLE'
                ? 'border-rose-500/30 bg-rose-500/[0.02]'
                : optB.feasibility === 'INSUFFICIENT_DATA'
                ? 'border-amber-500/30 bg-amber-500/[0.02]'
                : 'border-white/[0.08] hover:border-white/[0.16]'
            }`}
          >
            <div>
              {/* Card Header */}
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                <div className="flex items-center space-x-2">
                  <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    <Building2 className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="text-xs font-mono font-bold text-purple-400 uppercase tracking-wider">
                      Option B
                    </span>
                    <h4 className="text-sm font-bold text-white leading-tight">
                      Secondary Supplier
                    </h4>
                  </div>
                </div>
                {(() => {
                  const badge = getFeasibilityBadge(optB.feasibility);
                  return <StatusBadge status={badge.label} variant={badge.variant} dot={true} />;
                })()}
              </div>

              {/* Metrics */}
              <div className="py-4 space-y-3">
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <div className="text-[11px] text-slate-400 font-mono">
                    Vendor: <span className="text-slate-200 font-bold">{optB.supplier_name || 'Unassigned'}</span>
                  </div>
                  <div className="flex items-baseline space-x-2 mt-0.5">
                    <span className="text-xl font-mono font-extrabold text-white">
                      {formatCost(optB.estimated_total_cost)}
                    </span>
                    {optB.additional_cost_percentage != null && (
                      <span className="text-xs font-mono text-purple-300">
                        ({optB.additional_cost_percentage >= 0 ? '+' : ''}{optB.additional_cost_percentage}%)
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 font-mono">
                    Cost variance: {optB.additional_cost != null ? `${optB.additional_cost >= 0 ? '+' : ''}$${optB.additional_cost.toLocaleString()}` : 'N/A'}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] text-slate-500 block">Est. Delivery</span>
                    <span className="text-sm font-bold text-white">
                      {optB.estimated_delivery_days != null ? `${optB.estimated_delivery_days.toFixed(1)} days` : 'N/A'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] text-slate-500 block">Delay Risk</span>
                    <span className={`text-sm font-bold ${optB.risk_level === 'LOW' ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {optB.delay_probability != null ? `${Math.round(optB.delay_probability * 100)}% (${optB.risk_level})` : 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Constraint Violations if any */}
                {optB.constraint_violations?.length > 0 && (
                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300 space-y-1">
                    <span className="font-bold block">Constraint Violations:</span>
                    {optB.constraint_violations.map((v, i) => (
                      <div key={i}>• {v.message}</div>
                    ))}
                  </div>
                )}

                {/* Benefits / Trade-offs */}
                <div className="text-xs text-slate-300 leading-relaxed pt-1">
                  {optB.explanation}
                </div>
              </div>
            </div>

            {optB.is_recommended && (
              <div className="mt-2 pt-3 border-t border-emerald-500/20 text-center text-xs font-mono font-bold text-emerald-400">
                ★ Prescribed Choice
              </div>
            )}
          </div>
        )}

        {/* Card C: Delay Product Launch */}
        {optC && (
          <div
            className={`glass-card p-5 rounded-2xl border transition-all duration-300 flex flex-col justify-between ${
              optC.is_recommended
                ? 'border-emerald-500/50 bg-emerald-500/[0.04] shadow-[0_0_25px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/30'
                : optC.feasibility === 'INFEASIBLE'
                ? 'border-rose-500/30 bg-rose-500/[0.02]'
                : optC.feasibility === 'INSUFFICIENT_DATA'
                ? 'border-amber-500/30 bg-amber-500/[0.02]'
                : 'border-white/[0.08] hover:border-white/[0.16]'
            }`}
          >
            <div>
              {/* Card Header */}
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                <div className="flex items-center space-x-2">
                  <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <CalendarClock className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wider">
                      Option C
                    </span>
                    <h4 className="text-sm font-bold text-white leading-tight">
                      Delay Product Launch
                    </h4>
                  </div>
                </div>
                {(() => {
                  const badge = getFeasibilityBadge(optC.feasibility);
                  return <StatusBadge status={badge.label} variant={badge.variant} dot={true} />;
                })()}
              </div>

              {/* Metrics */}
              <div className="py-4 space-y-3">
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <div className="text-[11px] text-slate-400 font-mono">Direct Freight Expenditure</div>
                  <div className="flex items-baseline space-x-2 mt-0.5">
                    <span className="text-xl font-mono font-extrabold text-white">
                      {formatCost(optC.estimated_total_cost)}
                    </span>
                    <span className="text-xs font-mono text-emerald-400">(+$0 freight)</span>
                  </div>
                  <div className="text-[11px] text-amber-300 mt-1 font-mono flex items-center space-x-1">
                    <AlertTriangle className="h-3 w-3 shrink-0" />
                    <span>Commercial loss: Unquantified</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] text-slate-500 block">Milestone Shift</span>
                    <span className="text-sm font-bold text-amber-400">
                      +{optC.schedule_impact_days != null ? optC.schedule_impact_days.toFixed(1) : 0} days
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] text-slate-500 block">Est. Arrival</span>
                    <span className="text-sm font-bold text-white">
                      {optC.estimated_delivery_days != null ? `${optC.estimated_delivery_days.toFixed(1)} days` : 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Constraint Violations if any */}
                {optC.constraint_violations?.length > 0 && (
                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300 space-y-1">
                    <span className="font-bold block">Constraint Violations:</span>
                    {optC.constraint_violations.map((v, i) => (
                      <div key={i}>• {v.message}</div>
                    ))}
                  </div>
                )}

                {/* Benefits / Trade-offs */}
                <div className="text-xs text-slate-300 leading-relaxed pt-1">
                  {optC.explanation}
                </div>
              </div>
            </div>

            {optC.is_recommended && (
              <div className="mt-2 pt-3 border-t border-emerald-500/20 text-center text-xs font-mono font-bold text-emerald-400">
                ★ Prescribed Choice
              </div>
            )}
          </div>
        )}
      </div>

      {/* Comparative Trade-off Matrix */}
      <div className="glass-card p-5 rounded-2xl border border-white/[0.08]">
        <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-2">
          <Layers className="h-4 w-4 text-red-400" />
          <span>Strategic Decision Trade-off Comparison</span>
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400">
                <th className="pb-2">Option</th>
                <th className="pb-2">Mode / Vendor</th>
                <th className="pb-2">Total Cost</th>
                <th className="pb-2">Lead Time</th>
                <th className="pb-2">Predicted Delay</th>
                <th className="pb-2">Objective Score (Z)</th>
                <th className="pb-2">Feasibility</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              <tr className="text-slate-300">
                <td className="py-2.5 font-bold text-slate-400">Baseline</td>
                <td className="py-2.5">{baseline?.transport_mode} ({baseline?.supplier_id})</td>
                <td className="py-2.5">{formatCost(baseline?.estimated_total_cost)}</td>
                <td className="py-2.5">{baseline?.planned_lead_time_days} days</td>
                <td className="py-2.5 text-rose-400">+{baseline?.predicted_delay_days} days ({baseline?.risk_level})</td>
                <td className="py-2.5 text-slate-500">Baseline</td>
                <td className="py-2.5"><span className="text-amber-400 font-semibold">At-Risk</span></td>
              </tr>
              {alternatives.map((opt) => (
                <tr
                  key={opt.option_id}
                  className={opt.is_recommended ? 'bg-emerald-500/[0.08] text-white font-semibold' : 'text-slate-300'}
                >
                  <td className="py-2.5 flex items-center space-x-1.5">
                    {opt.is_recommended && <Check className="h-3 w-3 text-emerald-400" />}
                    <span>Option {opt.option_id} ({opt.name})</span>
                  </td>
                  <td className="py-2.5">{opt.transport_mode || 'Road'} ({opt.supplier_name || opt.supplier_id || 'N/A'})</td>
                  <td className="py-2.5">{formatCost(opt.estimated_total_cost)}</td>
                  <td className="py-2.5">{opt.estimated_delivery_days != null ? `${opt.estimated_delivery_days.toFixed(1)}d` : 'N/A'}</td>
                  <td className="py-2.5">
                    {opt.predicted_delay_days != null ? `+${opt.predicted_delay_days.toFixed(1)}d` : 'N/A'}
                  </td>
                  <td className="py-2.5">
                    {opt.objective_value != null ? `$${opt.objective_value.toLocaleString()}` : 'N/A'}
                  </td>
                  <td className="py-2.5">
                    <span
                      className={
                        opt.feasibility === 'FEASIBLE'
                          ? 'text-emerald-400 font-bold'
                          : opt.feasibility === 'INFEASIBLE'
                          ? 'text-rose-400 font-bold'
                          : 'text-amber-400'
                      }
                    >
                      {opt.feasibility}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Disclaimers & Model Notices */}
      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start space-x-2 text-[11px] text-slate-400">
        <Info className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-300">Operational Decision Notice: </span>
          Prescriptive alternatives are computed deterministically via mathematical programming and verified against hard budget, supplier capacity, and delivery constraints. Recommendations are advisory estimates designed for operations planners; they do not automatically execute financial transactions or carrier bookings.
        </div>
      </div>
    </div>
  );
}
