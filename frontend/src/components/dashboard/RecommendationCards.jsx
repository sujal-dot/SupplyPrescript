import React from 'react';
import { AlertCircle, ShieldAlert, Sparkles } from 'lucide-react';
import RecommendationCard from './RecommendationCard';

export default function RecommendationCards({
  alternatives = [],
  baseline = null,
  recommendedOptionId = null,
  onViewDetails,
  onSelectOption,
  onExecuteDecision,
  executedDecision = null,
  proposedDecision = null,
  loading = false,
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="glass-card p-6 rounded-2xl border border-white/[0.08] animate-pulse h-96 flex flex-col justify-between"
          >
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="h-10 w-10 bg-white/10 rounded-xl" />
                <div className="space-y-1.5 flex-1">
                  <div className="h-3 w-16 bg-white/10 rounded" />
                  <div className="h-5 w-32 bg-white/15 rounded" />
                </div>
              </div>
              <div className="h-20 bg-white/5 rounded-xl" />
              <div className="h-16 bg-white/5 rounded-xl" />
            </div>
            <div className="flex space-x-2 pt-4 border-t border-white/5">
              <div className="h-8 flex-1 bg-white/10 rounded-xl" />
              <div className="h-8 flex-1 bg-white/10 rounded-xl" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!alternatives || alternatives.length === 0) {
    return (
      <div className="glass-card p-8 rounded-2xl border border-white/[0.08] text-center flex flex-col items-center justify-center">
        <div className="p-3.5 rounded-2xl bg-amber-500/10 text-amber-400 mb-3 border border-amber-500/20">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h4 className="text-sm font-bold text-white tracking-tight">
          No Alternatives Available
        </h4>
        <p className="text-xs text-slate-400 mt-1.5 max-w-md">
          Optimization has not yet been executed for this shipment, or no decision pathways could be generated. Click &ldquo;Generate Recommendations&rdquo; to evaluate candidate options.
        </p>
      </div>
    );
  }

  // Check if ANY option is feasible
  const hasFeasible = alternatives.some((opt) => {
    const status = (opt.status || opt.feasibility || '').toUpperCase();
    return status === 'FEASIBLE';
  });

  return (
    <div className="space-y-4">
      {/* Notice if NO options are feasible */}
      {!hasFeasible && (
        <div className="glass-card p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 flex items-center space-x-3 text-xs text-rose-300">
          <ShieldAlert className="h-5 w-5 text-rose-400 shrink-0" />
          <div>
            <strong className="font-bold text-rose-200">Zero Feasible Alternatives:</strong>{' '}
            All evaluated candidate alternatives violate one or more hard operational constraints (e.g. budget ceiling, lead time SLA, or supplier capacity). No action may be automatically approved without relaxing constraints.
          </div>
        </div>
      )}

      {/* 3-Card Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {alternatives.map((option) => {
          const isRec =
            option.is_recommended ||
            option.option_id === recommendedOptionId ||
            (recommendedOptionId == null && option.option_id === 'A');

          return (
            <RecommendationCard
              key={option.option_id || option.strategy}
              option={option}
              baseline={baseline}
              isRecommended={Boolean(isRec)}
              onViewDetails={onViewDetails}
              onSelectOption={onSelectOption}
              onExecuteDecision={onExecuteDecision}
              executedDecision={executedDecision}
              proposedDecision={proposedDecision}
            />
          );
        })}
      </div>
    </div>
  );
}
