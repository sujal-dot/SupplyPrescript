import React from 'react';
import {
  X,
  Sparkles,
  Plane,
  Building2,
  CalendarClock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  DollarSign,
  Clock,
  Layers,
  FileText,
  ShieldCheck,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';

export default function RecommendationDetailsModal({
  option = null,
  baseline = null,
  isOpen = false,
  onClose,
  onSelectOption,
  onExecuteDecision,
  executedDecision = null,
  proposedDecision = null,
}) {
  if (!isOpen || !option) return null;

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
    risk_level,
    objective_value,
    cost_breakdown = {},
    constraint_violations = [],
    assumptions = [],
    explanation,
    is_recommended,
  } = option;

  const resolvedFeas = (status || feasibility || 'UNKNOWN').toUpperCase();
  const isFeasible = resolvedFeas === 'FEASIBLE';
  const isSelected = proposedDecision?.option_id === option_id;
  const isExecuted = executedDecision?.option_id === option_id;

  const formatCurrency = (val) => {
    if (val == null) return '—';
    return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getStrategyIcon = () => {
    if (strategy === 'AIR_FREIGHT' || option_id === 'A') return Plane;
    if (strategy === 'SECONDARY_SUPPLIER' || option_id === 'B') return Building2;
    return CalendarClock;
  };
  const Icon = getStrategyIcon();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-card w-full max-w-2xl max-h-[90vh] rounded-[28px] border border-white/[0.16] flex flex-col shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8),inset_0_1px_1.5px_rgba(255,255,255,0.35)] overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-white/[0.08] flex items-start justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="p-3 rounded-2xl bg-red-500/20 text-red-300 border border-red-500/30">
              <Icon className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-red-300 font-bold bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20">
                  Option {option_id}
                </span>
                {is_recommended && (
                  <span className="text-[10px] font-bold uppercase tracking-wider text-white bg-gradient-to-r from-red-600 to-rose-600 px-2 py-0.5 rounded-full shadow-sm">
                    Recommended
                  </span>
                )}
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight mt-1">
                {name || strategy}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs">
          {/* Feasibility & Top Telemetry */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Feasibility Status
              </span>
              <div className="flex items-center space-x-1 mt-1 font-bold">
                {isFeasible ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400">FEASIBLE</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-3.5 w-3.5 text-rose-400" />
                    <span className="text-rose-400">{resolvedFeas}</span>
                  </>
                )}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Total Expenditure
              </span>
              <span className="text-sm font-bold text-white font-mono mt-1 block">
                {formatCurrency(estimated_total_cost)}
              </span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Delivery Duration
              </span>
              <span className="text-sm font-bold text-red-300 font-mono mt-1 block">
                {estimated_delivery_days != null ? `${Number(estimated_delivery_days).toFixed(1)} days` : '—'}
              </span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Objective Score Z
              </span>
              <span className="text-sm font-bold text-slate-200 font-mono mt-1 block">
                {objective_value != null ? `$${Number(objective_value).toLocaleString(undefined, { minimumFractionDigits: 1 })}` : '—'}
              </span>
            </div>
          </div>

          {/* Business Rationale & Explanation */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center space-x-1.5">
              <FileText className="h-3.5 w-3.5 text-red-400" />
              <span>Operational Justification</span>
            </h4>
            <p className="text-slate-300 leading-relaxed bg-white/[0.02] p-4 rounded-xl border border-white/[0.04]">
              {explanation || 'Strategic decision generated via mixed-integer mathematical programming.'}
            </p>
          </div>

          {/* Itemized Cost Breakdown */}
          {cost_breakdown && Object.keys(cost_breakdown).length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center space-x-1.5">
                <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
                <span>Itemized Cost Decomposition</span>
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {Object.entries(cost_breakdown).map(([k, v]) => (
                  <div key={k} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                      {k.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs font-mono font-bold text-white mt-0.5 block">
                      {formatCurrency(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Constraint Violations (if any) */}
          {constraint_violations && constraint_violations.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-rose-300 font-mono flex items-center space-x-1.5">
                <XCircle className="h-3.5 w-3.5 text-rose-400" />
                <span>Violated Hard Business Constraints</span>
              </h4>
              <div className="space-y-2">
                {constraint_violations.map((cv, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-200 text-xs"
                  >
                    <div className="flex items-center justify-between font-bold">
                      <span>{cv.constraint_name}</span>
                      <span className="font-mono text-rose-300">
                        Actual: {cv.actual_value} &gt; Limit: {cv.limit_value}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-rose-300/80">{cv.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assumptions */}
          {assumptions && assumptions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center space-x-1.5">
                <Layers className="h-3.5 w-3.5 text-red-400" />
                <span>Key Assumptions &amp; Model Inputs</span>
              </h4>
              <ul className="list-disc list-inside space-y-1 text-slate-400 bg-white/[0.02] p-3.5 rounded-xl border border-white/[0.04]">
                {assumptions.map((asm, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {asm}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="p-5 border-t border-white/[0.08] flex items-center justify-between">
          <GlassButton variant="secondary" size="sm" onClick={onClose}>
            Close
          </GlassButton>

          {isFeasible ? (
            <GlassButton
              variant="primary"
              size="sm"
              icon={Sparkles}
              disabled={isExecuted || isSelected}
              onClick={() => {
                onClose();
                (onExecuteDecision || onSelectOption)?.(option);
              }}
            >
              {isExecuted ? 'Already Recorded' : isSelected ? 'Already Proposed' : 'Execute Strategic Decision'}
            </GlassButton>
          ) : (
            <span className="text-xs text-rose-400 font-semibold flex items-center space-x-1">
              <XCircle className="h-3.5 w-3.5" />
              <span>Infeasible options cannot be executed</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
