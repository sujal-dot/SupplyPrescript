import React, { useState } from 'react';
import {
  Cpu,
  Play,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  HelpCircle,
  Clock,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Sliders,
} from 'lucide-react';

export default function ModelEvaluationPanel({
  evaluationResult = null,
  onEvaluate = () => {},
  loading = false,
  datasetVersions = [],
}) {
  const [selectedModelVersion, setSelectedModelVersion] = useState('v1.0.0');
  const [selectedDatasetVersion, setSelectedDatasetVersion] = useState('');
  const [threshold, setThreshold] = useState(10);

  const handleRunEvaluation = (e) => {
    e.preventDefault();
    onEvaluate({
      model_version: selectedModelVersion,
      dataset_version: selectedDatasetVersion || null,
      min_sample_threshold: Number(threshold) || 10,
    });
  };

  const evalData = evaluationResult;
  const isEvaluated = evalData && evalData.status === 'EVALUATED';
  const isInsufficient = evalData && evalData.status === 'INSUFFICIENT_DATA';
  const hasWarnings = Array.isArray(evalData?.warnings) && evalData.warnings.length > 0;

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden mb-6">
      {/* Header */}
      <div className="p-5 border-b border-white/[0.08] flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-violet-500/15 border border-violet-400/30 text-violet-300">
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Continuous Model Evaluation & Drift Diagnostics
            </h3>
            <p className="text-xs text-slate-400">
              Evaluate ML delay predictions against ground-truth delivery observations
            </p>
          </div>
        </div>

        {/* Evaluation Configuration Controls */}
        <form onSubmit={handleRunEvaluation} className="flex flex-wrap items-center gap-2.5">
          {/* Model Version Dropdown */}
          <div className="flex items-center space-x-1.5">
            <span className="text-xs text-slate-400 font-mono">Model:</span>
            <select
              value={selectedModelVersion}
              onChange={(e) => setSelectedModelVersion(e.target.value)}
              aria-label="Evaluation Model Version"
              className="bg-slate-900/80 border border-white/10 rounded-xl text-xs text-red-300 font-mono py-1.5 px-2.5 focus:outline-none focus:border-red-500 transition-colors"
            >
              <option value="v1.0.0">v1.0.0</option>
              <option value="v1.0">v1.0</option>
            </select>
          </div>

          {/* Dataset Snapshot Selector */}
          <div className="flex items-center space-x-1.5">
            <span className="text-xs text-slate-400 font-mono">Dataset:</span>
            <select
              value={selectedDatasetVersion}
              onChange={(e) => setSelectedDatasetVersion(e.target.value)}
              aria-label="Evaluation Dataset Version"
              className="bg-slate-900/80 border border-white/10 rounded-xl text-xs text-slate-300 font-mono py-1.5 px-2.5 focus:outline-none focus:border-red-500 transition-colors"
            >
              <option value="">All Verified Actuals</option>
              {datasetVersions.map((ds) => (
                <option key={ds.dataset_version} value={ds.dataset_version}>
                  {ds.dataset_version} ({ds.eligible_count} obs)
                </option>
              ))}
            </select>
          </div>

          {/* Sample Threshold */}
          <div className="flex items-center space-x-1.5">
            <span className="text-xs text-slate-400 font-mono" title="Minimum sample size for conclusive metrics">
              Min N:
            </span>
            <input
              type="number"
              min="1"
              max="500"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              aria-label="Minimum sample size threshold"
              className="w-14 bg-slate-900/80 border border-white/10 rounded-xl text-xs text-slate-200 font-mono py-1.5 px-2 text-center focus:outline-none focus:border-red-500"
            />
          </div>

          {/* Trigger Button */}
          <button
            type="submit"
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-violet-600 to-red-600 hover:from-violet-500 hover:to-red-500 text-white text-xs font-semibold shadow-md transition-all disabled:opacity-50"
          >
            {loading ? (
              <>
                <Clock className="h-3.5 w-3.5 animate-spin" />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>Evaluate</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Main Panel Content */}
      <div className="p-5">
        {!evalData && !loading ? (
          <div className="py-8 text-center text-slate-500">
            <Sliders className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-400">Ready for Model Performance Evaluation</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Select a model version and click <span className="text-red-400 font-medium">Evaluate</span> to compute
              Mean Absolute Error, RMSE, and directional bias against verified shipment delivery outcomes.
            </p>
          </div>
        ) : isInsufficient ? (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300">
            <div className="flex items-center space-x-2 mb-2 font-bold text-sm">
              <AlertCircle className="h-4 w-4 text-amber-400 flex-shrink-0" />
              <span>Insufficient Ground Truth for Model {evalData.model_version}</span>
            </div>
            <p className="text-xs text-amber-200/90 leading-relaxed mb-3">
              {evalData.interpretation}
            </p>
            {hasWarnings && (
              <ul className="list-disc list-inside text-xs space-y-1 text-amber-400/90 font-mono">
                {evalData.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            )}
          </div>
        ) : isEvaluated ? (
          <div>
            {/* Status bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-4 mb-4 border-b border-white/[0.06]">
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Evaluation Complete</span>
                </span>
                <span className="font-mono text-xs text-red-300 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
                  {evalData.model_version}
                </span>
                <span className="text-xs text-slate-400">
                  ({evalData.evaluated_count} verified observations)
                </span>
                {evalData.is_preliminary && (
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[11px] font-medium">
                    <AlertTriangle className="h-3 w-3 text-amber-400" />
                    <span>Preliminary Evaluation (&lt;{threshold} samples)</span>
                  </span>
                )}
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                {evalData.evaluation_timestamp ? new Date(evalData.evaluation_timestamp).toLocaleString() : ''}
              </div>
            </div>

            {/* Metrics Cards Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              {/* MAE */}
              <div className="glass-card p-3.5 rounded-xl border border-white/[0.08]">
                <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
                  <span>MAE (Absolute Error)</span>
                  <HelpCircle className="h-3 w-3 text-slate-500" title="Mean Absolute Error in days" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {evalData.mae != null ? `${evalData.mae.toFixed(2)} d` : '—'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Average magnitude of error</div>
              </div>

              {/* RMSE */}
              <div className="glass-card p-3.5 rounded-xl border border-white/[0.08]">
                <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
                  <span>RMSE</span>
                  <HelpCircle className="h-3 w-3 text-slate-500" title="Root Mean Squared Error (penalizes large outlier misses)" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {evalData.rmse != null ? `${evalData.rmse.toFixed(2)} d` : '—'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Variance-sensitive metric</div>
              </div>

              {/* Mean Signed Error / Directional Bias */}
              <div className="glass-card p-3.5 rounded-xl border border-white/[0.08]">
                <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
                  <span>Directional Bias</span>
                  {evalData.mean_signed_error != null && evalData.mean_signed_error > 0 ? (
                    <TrendingUp className="h-3.5 w-3.5 text-rose-400" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5 text-emerald-400" />
                  )}
                </div>
                <div className="text-2xl font-bold font-mono">
                  {evalData.mean_signed_error != null ? (
                    <span className={evalData.mean_signed_error > 0 ? 'text-rose-400' : 'text-emerald-400'}>
                      {evalData.mean_signed_error > 0
                        ? `+${evalData.mean_signed_error.toFixed(2)} d`
                        : `${evalData.mean_signed_error.toFixed(2)} d`}
                    </span>
                  ) : (
                    '—'
                  )}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {evalData.mean_signed_error != null ? (
                    evalData.mean_signed_error > 0 ? 'Underpredicting (arriving late)' : 'Overpredicting (arriving early)'
                  ) : (
                    'No bias calculated'
                  )}
                </div>
              </div>

              {/* Median Absolute Error & Range */}
              <div className="glass-card p-3.5 rounded-xl border border-white/[0.08]">
                <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
                  <span>Median AE & Range</span>
                  <Sliders className="h-3 w-3 text-slate-500" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {evalData.median_absolute_error != null
                    ? `${evalData.median_absolute_error.toFixed(2)} d`
                    : '—'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
                  Range: [{evalData.min_error != null ? evalData.min_error.toFixed(1) : '—'},{' '}
                  {evalData.max_error != null ? evalData.max_error.toFixed(1) : '—'}] d
                </div>
              </div>
            </div>

            {/* Warnings list */}
            {hasWarnings && (
              <div className="mb-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
                <div className="flex items-center space-x-1.5 font-bold mb-1">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                  <span>Evaluation Quality Advisories:</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 text-amber-200/90">
                  {evalData.warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Human-Readable Interpretation */}
            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs text-slate-300 leading-relaxed mb-4">
              <span className="font-semibold text-white">Model Evaluation Assessment: </span>
              {evalData.interpretation}
            </div>

            {/* Governance & Sign Convention Note */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] text-slate-500 border-t border-white/[0.04] pt-3">
              <div className="flex items-center space-x-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                <span>
                  <strong>Continuous Learning Policy:</strong> Model evaluation is strictly diagnostic. Automated retraining,
                  promotion, or replacement of production weights is disabled pending human engineering sign-off.
                </span>
              </div>
              <div className="font-mono text-slate-400 text-[10px]">
                Sign convention: error = actual - predicted
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
