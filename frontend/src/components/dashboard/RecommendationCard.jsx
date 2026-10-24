import React from 'react';
import {
  Plane,
  Building2,
  CalendarClock,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  DollarSign,
  Shield,
  Layers,
  ArrowRight,
  Info,
  Check,
} from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';
import GlassButton from '../ui/GlassButton';

export default function RecommendationCard({
  option,
  baseline = null,
  isRecommended = false,
  onViewDetails,
  onSelectOption,
  onExecuteDecision,
  executedDecision = null,
  proposedDecision = null,
}) {
  if (!option) return null;

  const {
    option_id,
    strategy,
    name,
    status = 'FEASIBLE',
    feasibility,
    estimated_total_cost,
    additional_cost,
    additional_cost_percentage,
    estimated_delivery_days,
    schedule_impact_days,
    delay_probability,
    predicted_delay_days,
    risk_level,
    constraint_violations = [],
    assumptions = [],
    explanation,
    is_recommended,
  } = option;

  const resolvedFeasibility = (status || feasibility || 'UNKNOWN').toUpperCase();
  const isFeasible = resolvedFeasibility === 'FEASIBLE';
  const isSelected = proposedDecision?.option_id === option_id;
  const isExecuted = executedDecision?.option_id === option_id;

  // Icons based on strategy
  const getIcon = () => {
    switch (strategy) {
      case 'AIR_FREIGHT':
        return Plane;
      case 'SECONDARY_SUPPLIER':
        return Building2;
      case 'DELAY_LAUNCH':
        return CalendarClock;
      default:
        if (option_id === 'A') return Plane;
        if (option_id === 'B') return Building2;
        return CalendarClock;
    }
  };
  const Icon = getIcon();

  // Feasibility status badge info
  const getFeasibilityDisplay = () => {
    switch (resolvedFeasibility) {
      case 'FEASIBLE':
        return {
          label: 'FEASIBLE',
          sublabel: 'Constraints Passed',
          variant: 'success',
          icon: CheckCircle2,
          iconColor: 'text-emerald-400',
        };
      case 'INFEASIBLE':
        return {
          label: 'INFEASIBLE',
          sublabel: 'Constraint Violations',
          variant: 'error',
          icon: XCircle,
          iconColor: 'text-rose-400',
        };
      case 'INSUFFICIENT_DATA':
        return {
          label: 'INSUFFICIENT DATA',
          sublabel: 'Requires Configuration',
          variant: 'warning',
          icon: HelpCircle,
          iconColor: 'text-amber-400',
        };
      default:
        return {
          label: resolvedFeasibility,
          sublabel: 'Evaluation Pending',
          variant: 'neutral',
          icon: AlertTriangle,
          iconColor: 'text-slate-400',
        };
    }
  };

  const feasibilityInfo = getFeasibilityDisplay();
  const FeasIcon = feasibilityInfo.icon;

  // Format currency
  const formatCost = (val) => {
    if (val == null) return 'Requires configuration';
    return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Format delta
  const formatDelta = (val, pct) => {
    if (val == null) return null;
    const num = Number(val);
    const sign = num > 0 ? '+' : '';
    const pctStr = pct != null ? ` (${sign}${Number(pct).toFixed(1)}%)` : '';
    return `${sign}$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${pctStr}`;
  };

  // Format delivery
  const formatDays = (days) => {
    if (days == null) return 'Not available';
    return `${Number(days).toFixed(1)} days`;
  };

  return (
    <div
      className={`glass-card p-6 rounded-2xl flex flex-col justify-between transition-all duration-300 relative ${
        isRecommended && isFeasible
          ? 'border-red-500/50 bg-gradient-to-b from-red-500/10 via-slate-900/60 to-transparent shadow-xl shadow-red-950/40 ring-1 ring-red-500/30'
          : 'border-white/[0.08] hover:border-white/[0.18]'
      }`}
    >
      {/* Recommended Winning Badge */}
      {isRecommended && isFeasible && (
        <div className="absolute -top-3 left-6 px-3 py-1 rounded-full bg-gradient-to-r from-red-600 to-rose-600 text-white text-[11px] font-bold tracking-wide shadow-md shadow-red-500/30 flex items-center space-x-1.5 border border-white/20">
          <Sparkles className="h-3 w-3 animate-pulse" />
          <span>RECOMMENDED ACTION</span>
        </div>
      )}

      {/* Card Header: Strategy Title & Feasibility Badge */}
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3 pt-1">
          <div className="flex items-center space-x-3">
            <div
              className={`p-2.5 rounded-xl border shrink-0 ${
                isRecommended && isFeasible
                  ? 'bg-red-500/20 text-red-300 border-red-500/40 shadow-lg shadow-red-500/20'
                  : 'bg-white/[0.05] text-slate-300 border-white/[0.1]'
              }`}
            >
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold block">
                Option {option_id}
              </span>
              <h3 className="text-base font-bold text-white tracking-tight leading-snug">
                {name || strategy}
              </h3>
            </div>
          </div>

          {/* Feasibility Indicator with text and icon */}
          <div
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full border text-[11px] font-bold shrink-0"
            title={feasibilityInfo.sublabel}
          >
            <FeasIcon className={`h-3.5 w-3.5 ${feasibilityInfo.iconColor}`} />
            <span className={feasibilityInfo.iconColor}>{feasibilityInfo.label}</span>
          </div>
        </div>

        {/* Primary Metrics: Cost & Delivery impact */}
        <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          {/* Estimated Total Cost */}
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
              Estimated Total Cost
            </span>
            <span className="text-base font-bold text-white font-mono mt-0.5 block">
              {formatCost(estimated_total_cost)}
            </span>
            {additional_cost != null && (
              <span
                className={`text-[11px] font-mono mt-0.5 block ${
                  Number(additional_cost) > 0
                    ? 'text-rose-400'
                    : Number(additional_cost) < 0
                    ? 'text-emerald-400'
                    : 'text-slate-400'
                }`}
              >
                {formatDelta(additional_cost, additional_cost_percentage)}
              </span>
            )}
          </div>

          {/* Estimated Delivery Time */}
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
              Estimated Delivery
            </span>
            <span className="text-base font-bold text-red-300 font-mono mt-0.5 block">
              {formatDays(estimated_delivery_days)}
            </span>
            {schedule_impact_days != null && (
              <span className="text-[11px] font-mono text-slate-400 mt-0.5 block">
                {Number(schedule_impact_days) <= 0
                  ? `${Math.abs(Number(schedule_impact_days)).toFixed(1)}d faster`
                  : `+${Number(schedule_impact_days).toFixed(1)}d delay`}
              </span>
            )}
          </div>
        </div>

        {/* Risk & Constraints Quick Check */}
        <div className="space-y-2 pt-1">
          {/* Risk Tier */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Risk Assessment:</span>
            <div className="flex items-center space-x-1.5 font-mono">
              <span className="text-slate-200 font-semibold">{risk_level || 'LOW'}</span>
              {delay_probability != null && (
                <span className="text-slate-400 text-[11px]">
                  ({Math.round(Number(delay_probability) * 100)}% delay risk)
                </span>
              )}
            </div>
          </div>

          {/* Constraint Snapshot */}
          <div className="p-2.5 rounded-lg bg-black/20 border border-white/[0.04] space-y-1 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium">Budget Check:</span>
              <span
                className={`font-mono font-bold flex items-center space-x-1 ${
                  constraint_violations.some((v) => v.constraint_name.toLowerCase().includes('budget'))
                    ? 'text-rose-400'
                    : isFeasible
                    ? 'text-emerald-400'
                    : 'text-slate-400'
                }`}
              >
                {constraint_violations.some((v) => v.constraint_name.toLowerCase().includes('budget')) ? (
                  <>
                    <XCircle className="h-3 w-3 inline" />
                    <span>FAIL</span>
                  </>
                ) : isFeasible ? (
                  <>
                    <CheckCircle2 className="h-3 w-3 inline" />
                    <span>PASS</span>
                  </>
                ) : (
                  <span>UNVERIFIED</span>
                )}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium">Capacity & SLA:</span>
              <span
                className={`font-mono font-bold flex items-center space-x-1 ${
                  constraint_violations.some((v) =>
                    v.constraint_name.toLowerCase().includes('capacity') ||
                    v.constraint_name.toLowerCase().includes('delivery')
                  )
                    ? 'text-rose-400'
                    : isFeasible
                    ? 'text-emerald-400'
                    : 'text-slate-400'
                }`}
              >
                {constraint_violations.some((v) =>
                  v.constraint_name.toLowerCase().includes('capacity') ||
                  v.constraint_name.toLowerCase().includes('delivery')
                ) ? (
                  <>
                    <XCircle className="h-3 w-3 inline" />
                    <span>FAIL</span>
                  </>
                ) : isFeasible ? (
                  <>
                    <CheckCircle2 className="h-3 w-3 inline" />
                    <span>PASS</span>
                  </>
                ) : (
                  <span>UNVERIFIED</span>
                )}
              </span>
            </div>
          </div>

          {/* Concise Strategy Explanation */}
          <p className="text-xs text-slate-300/90 line-clamp-3 leading-relaxed pt-1">
            {explanation || 'Strategic decision alternative evaluated by mixed-integer mathematical optimization.'}
          </p>
        </div>
      </div>

      {/* Card Actions: View Details and Execute Decision */}
      <div className="pt-5 mt-4 border-t border-white/[0.08] flex items-center space-x-2.5">
        <GlassButton
          variant="secondary"
          size="sm"
          onClick={() => onViewDetails?.(option)}
          className="flex-1"
        >
          View Details
        </GlassButton>

        {/* Safe Execution Button */}
        {isExecuted ? (
          <div className="px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-mono font-bold flex items-center space-x-1.5 shrink-0">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>RECORDED</span>
          </div>
        ) : isSelected ? (
          <div className="px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold flex items-center space-x-1.5 shrink-0">
            <Check className="h-3.5 w-3.5" />
            <span>Proposed</span>
          </div>
        ) : (
          <GlassButton
            variant={isRecommended && isFeasible ? 'primary' : 'secondary'}
            size="sm"
            disabled={!isFeasible}
            onClick={() => (onExecuteDecision || onSelectOption)?.(option)}
            title={!isFeasible ? 'Infeasible option cannot be selected for execution' : 'Execute this strategic decision alternative'}
          >
            EXECUTE DECISION
          </GlassButton>
        )}
      </div>
    </div>
  );
}
