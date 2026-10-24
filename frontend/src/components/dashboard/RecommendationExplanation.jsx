import React from 'react';
import { Sparkles, Scale, Info, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function RecommendationExplanation({
  recommendedOption = null,
  baseline = null,
  reason = '',
  tradeOffs = '',
}) {
  if (!recommendedOption) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] text-xs text-slate-400">
        <div className="flex items-center space-x-2 text-slate-300 font-bold mb-1">
          <Info className="h-4 w-4 text-red-400" />
          <span>Decision Methodology</span>
        </div>
        <p>
          Select an active shipment and run optimization to view mathematical rationale, objective score trade-offs, and operational justification.
        </p>
      </div>
    );
  }

  const optionId = recommendedOption.option_id;
  const optionName = recommendedOption.name || recommendedOption.strategy;
  const objectiveScore = recommendedOption.objective_value != null ? Number(recommendedOption.objective_value).toFixed(2) : null;
  const displayReason = reason || recommendedOption.explanation || 'Option minimizes total supply-chain risk and expected delay while satisfying budget constraints.';
  const displayTradeOffs = tradeOffs || recommendedOption.trade_offs || 'Prioritizes delivery reliability and SLA compliance over nominal freight savings.';

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Recommendation Rationale &amp; Objective Formulation
            </h3>
            <p className="text-xs text-slate-400">
              Mixed-Integer Linear Programming (Day 12 &amp; Day 14) Decision Synthesis
            </p>
          </div>
        </div>

        {/* Objective Function Badge */}
        <div className="hidden sm:flex items-center space-x-2 bg-white/[0.03] border border-white/[0.06] px-3 py-1.5 rounded-xl text-xs font-mono">
          <span className="text-slate-400">Objective:</span>
          <span className="text-red-300 font-bold">
            min Z = C_total + C_delay + C_risk
          </span>
        </div>
      </div>

      <div className="p-5 space-y-4 text-xs">
        {/* Recommendation Justification Callout */}
        <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 space-y-2">
          <div className="flex items-center space-x-2 text-red-300 font-bold">
            <CheckCircle2 className="h-4 w-4 text-red-400" />
            <span>Recommended Option {optionId}: {optionName}</span>
            {objectiveScore && (
              <span className="text-[11px] font-mono font-normal text-slate-400 ml-auto">
                Evaluated Score Z = ${Number(objectiveScore).toLocaleString()}
              </span>
            )}
          </div>
          <p className="text-slate-300 leading-relaxed text-xs">
            {displayReason}
          </p>
        </div>

        {/* Trade-Off Analysis */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
          <div className="flex items-center space-x-2 text-slate-200 font-bold">
            <Scale className="h-4 w-4 text-amber-400" />
            <span>Strategic Trade-Off Analysis</span>
          </div>
          <p className="text-slate-300 leading-relaxed text-xs">
            {displayTradeOffs}
          </p>
        </div>

        {/* Operational Uncertainty & Human-in-the-Loop Notice */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/[0.06] flex items-start space-x-3 text-[11px] text-slate-400">
          <Info className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong className="text-slate-300">Operational Verification Notice:</strong> Recommendations are computed from probabilistic ML delay models and deterministic PuLP solver constraints. Final freight rerouting or supplier PO issuance requires explicit manager confirmation and PO authorization.
          </p>
        </div>
      </div>
    </div>
  );
}
