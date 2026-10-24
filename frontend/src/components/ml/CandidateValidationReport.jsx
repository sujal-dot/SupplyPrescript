import React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  HelpCircle,
} from 'lucide-react';

export default function CandidateValidationReport({
  validationResult = {},
  candidateVersion = 'v1.1',
  baselineVersion = 'v1.0',
}) {
  const res = validationResult || {};
  const isAccepted = res.accepted === true;
  const checks = res.checks || {};
  const errors = Array.isArray(res.errors) ? res.errors : [];
  const comp = res.comparison || {};

  const candMae = comp.candidate_mae != null ? Number(comp.candidate_mae) : null;
  const baseMae = comp.baseline_mae != null ? Number(comp.baseline_mae) : null;
  const maeImprovePct = comp.mae_improvement_pct != null ? Number(comp.mae_improvement_pct) : null;

  const candRmse = comp.candidate_rmse != null ? Number(comp.candidate_rmse) : null;
  const baseRmse = comp.baseline_rmse != null ? Number(comp.baseline_rmse) : null;
  const rmseRegressPct = comp.rmse_regression_pct != null ? Number(comp.rmse_regression_pct) : null;

  const checkLabels = {
    artifact_integrity: 'Artifact Integrity & SHA-256 Checksums',
    smoke_test_predictions: 'Inference Smoke Test (Valid Output Shape & Bounds)',
    leakage_check: 'Data Leakage Blacklist Verification',
    minimum_sample_size: 'Independent Holdout Evaluation Sample Size',
    mae_improvement: 'Delay MAE Improvement or Non-Inferiority',
    rmse_within_limit: 'Secondary RMSE Metric Within Tolerance (<=10%)',
  };

  return (
    <div className="glass-card p-5 rounded-2xl border border-white/[0.08] mb-6">
      {/* Header with Status Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 mb-4 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-4 w-4 text-red-400" />
            <h4 className="text-sm font-bold text-white tracking-tight">
              Independent Candidate Validation Report
            </h4>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-300">
              {candidateVersion} vs {baselineVersion}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Empirical benchmarking on untouched chronological holdout evaluation data
          </p>
        </div>

        <div>
          {isAccepted ? (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-bold">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>PROMOTE ELIGIBLE</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-bold">
              <XCircle className="h-4 w-4 text-rose-400" />
              <span>REJECT CANDIDATE</span>
            </span>
          )}
        </div>
      </div>

      {/* Metrics Benchmarking Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        {/* Candidate MAE */}
        <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05]">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">
            Candidate MAE ({candidateVersion})
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {candMae != null ? `${candMae.toFixed(3)} d` : '—'}
          </div>
          <div className="text-[11px] mt-0.5 font-mono">
            {maeImprovePct != null ? (
              <span className={maeImprovePct >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                {maeImprovePct >= 0 ? `+${maeImprovePct.toFixed(1)}%` : `${maeImprovePct.toFixed(1)}%`} vs baseline
              </span>
            ) : null}
          </div>
        </div>

        {/* Baseline MAE */}
        <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05]">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">
            Baseline MAE ({baselineVersion})
          </div>
          <div className="text-xl font-bold font-mono text-slate-300">
            {baseMae != null ? `${baseMae.toFixed(3)} d` : '—'}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Production benchmark</div>
        </div>

        {/* Candidate RMSE */}
        <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05]">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">
            Candidate RMSE
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {candRmse != null ? `${candRmse.toFixed(3)} d` : '—'}
          </div>
          <div className="text-[11px] mt-0.5 font-mono">
            {rmseRegressPct != null ? (
              <span className={rmseRegressPct <= 10.0 ? 'text-emerald-400' : 'text-rose-400'}>
                {rmseRegressPct > 0 ? `+${rmseRegressPct.toFixed(1)}%` : `${rmseRegressPct.toFixed(1)}%`} shift
              </span>
            ) : null}
          </div>
        </div>

        {/* Baseline RMSE */}
        <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05]">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">
            Baseline RMSE
          </div>
          <div className="text-xl font-bold font-mono text-slate-300">
            {baseRmse != null ? `${baseRmse.toFixed(3)} d` : '—'}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Production benchmark</div>
        </div>
      </div>

      {/* Validation Checks Checklist */}
      <div className="space-y-2 mb-4">
        <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Technical & Governance Acceptance Checklist
        </h5>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
          {Object.keys(checkLabels).map((key) => {
            const passed = checks[key] === true;
            return (
              <div
                key={key}
                className={`p-2.5 rounded-xl border flex items-center justify-between ${
                  passed
                    ? 'bg-emerald-500/5 border-emerald-500/20 text-slate-200'
                    : 'bg-rose-500/5 border-rose-500/20 text-rose-300'
                }`}
              >
                <span>{checkLabels[key]}</span>
                {passed ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Failure reasons if any */}
      {errors.length > 0 && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
          <div className="flex items-center space-x-1.5 font-bold mb-1">
            <AlertTriangle className="h-4 w-4 text-rose-400" />
            <span>Validation Rejection Rationales:</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-rose-200/90 font-mono text-[11px]">
            {errors.map((err, idx) => (
              <li key={idx}>{err}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
