import React from 'react';
import {
  Layers,
  Sparkles,
  RefreshCw,
  Clock,
  Sliders,
  ShieldAlert,
} from 'lucide-react';
import GlassButton from '../ui/GlassButton';

export default function CommandCenterHeader({
  lastUpdated = null,
  loading = false,
  onRefresh,
  scenarioId = 'baseline',
  onScenarioChange,
}) {
  const scenarios = [
    { id: 'baseline', label: 'Baseline (Balanced $50k)' },
    { id: 'budget_constrained', label: 'Budget-Constrained ($30k)' },
    { id: 'delay_sensitive', label: 'Delay-Sensitive (3-day max)' },
    { id: 'risk_averse', label: 'Risk-Averse (Reliability Focus)' },
    { id: 'expedited_service', label: 'Expedited Service (Fastest)' },
    { id: 'inventory_buffering', label: 'Inventory Buffering' },
  ];

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-white/[0.08]">
      {/* Brand & Titles */}
      <div className="flex items-start space-x-3.5">
        <div className="h-11 w-11 rounded-2xl bg-gradient-to-tr from-red-600 via-rose-600 to-red-500 flex items-center justify-center shadow-lg shadow-red-500/25 border border-white/20 shrink-0">
          <Layers className="h-6 w-6 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Command Center
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider font-bold rounded-full bg-red-500/20 text-red-300 border border-red-500/30">
              Live Operations
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Supply chain risk, optimization, and recommended actions.
          </p>
        </div>
      </div>

      {/* Controls & Telemetry */}
      <div className="flex flex-wrap items-center gap-2.5">
        {/* Scenario Selector */}
        <div className="flex items-center space-x-2 bg-white/[0.04] border border-white/[0.08] px-3 py-1.5 rounded-xl">
          <Sliders className="h-3.5 w-3.5 text-red-400 shrink-0" />
          <span className="text-xs text-slate-400 font-medium">Scenario:</span>
          <select
            value={scenarioId}
            onChange={(e) => onScenarioChange?.(e.target.value)}
            className="bg-transparent text-xs font-semibold text-red-300 focus:outline-none cursor-pointer pr-1"
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id} className="bg-[#0b1626] text-slate-200">
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {/* Last Updated Timestamp */}
        {lastUpdated && (
          <div className="hidden sm:flex items-center space-x-1.5 text-[11px] font-mono text-slate-400 bg-white/[0.03] border border-white/[0.06] px-2.5 py-1.5 rounded-xl">
            <Clock className="h-3 w-3 text-slate-500" />
            <span>Updated: {lastUpdated}</span>
          </div>
        )}

        {/* Refresh Action */}
        <GlassButton
          variant="secondary"
          size="sm"
          icon={RefreshCw}
          loading={loading}
          onClick={onRefresh}
        >
          Refresh
        </GlassButton>
      </div>
    </div>
  );
}
