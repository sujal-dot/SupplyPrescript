import React from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  Clock,
  Cpu,
  Info,
  Calendar,
  Layers,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import StatusBadge from '../ui/StatusBadge';

export default function PredictionResult({ result }) {
  if (!result) {
    return (
      <div className="glass-card p-8 rounded-2xl border border-white/[0.08] text-center flex flex-col items-center justify-center min-h-[380px]">
        <div className="p-4 rounded-2xl bg-white/[0.04] text-slate-400 border border-white/[0.08] mb-3">
          <Activity className="h-8 w-8 text-red-400/80" />
        </div>
        <h3 className="text-base font-bold text-white tracking-tight">
          Awaiting Scenario Submission
        </h3>
        <p className="text-xs text-slate-400 mt-1 max-w-sm">
          Select supplier, product, quantity, inventory, and transit mode in the form and click "Predict Shipment Risk" to generate active XGBoost inference.
        </p>
      </div>
    );
  }

  const {
    delay_probability = 0,
    predicted_delay_days = 0,
    risk = 'LOW',
    model_version = 'v1.0',
    prediction_id = '',
    prediction_timestamp = '',
    features_used = null,
  } = result;

  const probPct = Math.round(Number(delay_probability) * 100);
  const delayDays = Number(predicted_delay_days).toFixed(1);

  const riskConfigs = {
    LOW: {
      badgeVariant: 'success',
      border: 'border-emerald-500/30',
      glow: 'shadow-[0_0_30px_rgba(52,211,153,0.15)]',
      bgGrad: 'from-emerald-500/10 via-transparent to-transparent',
      textColor: 'text-emerald-400',
      barColor: 'bg-emerald-500',
      description: 'Low probability of shipment disruption (<30%). Standard transit expected.',
    },
    MEDIUM: {
      badgeVariant: 'warning',
      border: 'border-amber-500/30',
      glow: 'shadow-[0_0_30px_rgba(251,191,36,0.15)]',
      bgGrad: 'from-amber-500/10 via-transparent to-transparent',
      textColor: 'text-amber-400',
      barColor: 'bg-amber-500',
      description: 'Moderate risk of delay (30% to 69%). Monitor carrier milestones closely.',
    },
    HIGH: {
      badgeVariant: 'error',
      border: 'border-rose-500/30',
      glow: 'shadow-[0_0_30px_rgba(251,113,133,0.15)]',
      bgGrad: 'from-rose-500/10 via-transparent to-transparent',
      textColor: 'text-rose-400',
      barColor: 'bg-rose-500',
      description: 'Critical delay risk (≥70%). Consider inventory buffering or expedited transit.',
    },
  };

  const currentRisk = riskConfigs[risk] || riskConfigs.LOW;

  return (
    <div
      className={`glass-card p-6 rounded-2xl border transition-all duration-300 relative overflow-hidden bg-gradient-to-br ${currentRisk.bgGrad} ${currentRisk.border} ${currentRisk.glow}`}
    >
      {/* Top Banner */}
      <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <Cpu className="h-4 w-4 text-red-400" />
          <span className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            Shipment Risk Assessment
          </span>
        </div>
        <StatusBadge status={risk} variant={currentRisk.badgeVariant} dot={true} />
      </div>

      {/* Main Prediction Scorecards */}
      <div className="py-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Delay Probability */}
        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="text-xs text-slate-400 font-mono mb-1">
            Delay Probability
          </div>
          <div className="flex items-baseline space-x-2">
            <span className={`text-3xl font-extrabold font-mono ${currentRisk.textColor}`}>
              {probPct}%
            </span>
            <span className="text-xs text-slate-400">likelihood</span>
          </div>

          {/* Progress bar gauge */}
          <div className="w-full h-2 bg-white/10 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${currentRisk.barColor}`}
              style={{ width: `${Math.min(100, probPct)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
            <span>0% (Low)</span>
            <span>30%</span>
            <span>70% (High)</span>
            <span>100%</span>
          </div>
        </div>

        {/* Predicted Delay Duration */}
        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="text-xs text-slate-400 font-mono mb-1">
            Predicted Delay Duration
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold font-mono text-white">
              +{delayDays}
            </span>
            <span className="text-xs text-slate-300 font-medium">days</span>
          </div>

          <div className="mt-3 flex items-center space-x-2 text-xs text-slate-400">
            <Clock className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <span className="truncate">
              {delayDays > 0
                ? `Expected ${delayDays} days beyond planned lead time`
                : 'Projected to arrive on planned schedule'}
            </span>
          </div>
        </div>
      </div>

      {/* Audit Meta Tags */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 py-3 border-y border-white/[0.06] text-xs font-mono">
        <div>
          <span className="text-slate-500 block text-[10px]">Risk Tier</span>
          <span className={`font-bold ${currentRisk.textColor}`}>{risk}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">Active Model</span>
          <span className="text-slate-200 font-semibold">{model_version}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">Prediction Audit ID</span>
          <span className="text-red-300 font-semibold truncate block" title={prediction_id}>
            {prediction_id || 'PRED-LIVE'}
          </span>
        </div>
      </div>

      {/* Feature Explainability Section */}
      {features_used && (
        <div className="mt-4 pt-3">
          <div className="flex items-center space-x-1.5 mb-2 text-xs font-mono text-slate-400">
            <Layers className="h-3.5 w-3.5 text-red-400" />
            <span className="font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
              Resolved Model Features (No Data Leakage)
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
            <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-500 block text-[10px]">Supplier Rel.</span>
              <span className="text-white font-semibold">
                {Math.round(Number(features_used.supplier_reliability || 0) * 100)}%
              </span>
            </div>
            <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-500 block text-[10px]">Hist. Avg Delay</span>
              <span className="text-white font-semibold">
                {Number(features_used.historical_avg_delay || 0).toFixed(2)} d
              </span>
            </div>
            <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-500 block text-[10px]">Transit Mode</span>
              <span className="text-white font-semibold">
                {features_used.transport_mode || 'Road'}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-slate-500 block text-[10px]">Route Distance</span>
              <span className="text-white font-semibold">
                {Math.round(Number(features_used.distance || 0))} km
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Explainability & Limitations Disclaimers */}
      <div className="mt-4 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start space-x-2 text-[11px] text-slate-400">
        <Info className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-300">Model Estimation Notice: </span>
          This prediction is generated by production XGBoost classification and regression models trained on historical logistics telemetry. Outputs represent probabilistic estimates under given operational conditions, not guarantees.
        </div>
      </div>
    </div>
  );
}
