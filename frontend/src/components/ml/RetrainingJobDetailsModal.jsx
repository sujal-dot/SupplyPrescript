import React, { useState } from 'react';
import {
  X,
  FileText,
  Clock,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Zap,
} from 'lucide-react';
import CandidateValidationReport from './CandidateValidationReport';

export default function RetrainingJobDetailsModal({
  job = null,
  isOpen = false,
  onClose = () => {},
  onPromote = () => {},
  onRollback = () => {},
  promoting = false,
}) {
  const [rollbackConfirm, setRollbackConfirm] = useState(false);

  if (!isOpen || !job) return null;

  const canPromote = job.status === 'REGISTERED';
  const hasValidation = job.acceptance_result && typeof job.acceptance_result === 'object';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-md animate-fade-in">
      <div className="glass-card w-full max-w-3xl rounded-[28px] border border-white/[0.16] overflow-hidden shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8),inset_0_1px_1.5px_rgba(255,255,255,0.35)] max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-white tracking-tight font-mono">
                  {job.job_id}
                </h3>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-300">
                  {job.status}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Retraining Job Execution & Candidate Validation Audit
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-slate-900/60 rounded-xl border border-white/[0.06] font-mono">
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Parent Model</div>
              <div className="text-sm font-bold text-white">{job.parent_model_version}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Candidate Model</div>
              <div className="text-sm font-bold text-red-400">{job.candidate_model_version || 'None'}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Triggered By</div>
              <div className="text-sm font-bold text-slate-300 truncate">{job.triggered_by}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Dataset Fingerprint</div>
              <div className="text-sm font-bold text-emerald-400 truncate" title={job.dataset_version}>
                {job.dataset_version || 'N/A'}
              </div>
            </div>
          </div>

          {/* Trigger Rationale */}
          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
            <span className="font-semibold text-slate-200">Trigger Reason: </span>
            <span className="text-slate-300">{job.trigger_reason}</span>
          </div>

          {/* Failure reason alert if present */}
          {job.failure_reason && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300">
              <div className="flex items-center space-x-1.5 font-bold mb-1">
                <AlertTriangle className="h-4 w-4 text-rose-400" />
                <span>Job Failure / Rejection Note:</span>
              </div>
              <p className="font-mono text-[11px] text-rose-200/90">{job.failure_reason}</p>
            </div>
          )}

          {/* Candidate Validation Report */}
          {hasValidation && (
            <CandidateValidationReport
              validationResult={job.acceptance_result}
              candidateVersion={job.candidate_model_version || 'Candidate'}
              baselineVersion={job.parent_model_version}
            />
          )}

          {/* Controlled Promotion Action */}
          {canPromote && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h5 className="font-bold text-white text-sm">Approve Candidate Promotion</h5>
                <p className="text-slate-300 text-xs mt-0.5">
                  Candidate version {job.candidate_model_version} has passed all technical acceptance checks.
                </p>
              </div>
              <button
                onClick={() => onPromote(job.job_id)}
                disabled={promoting}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-red-500 hover:from-emerald-400 hover:to-red-400 text-slate-950 font-bold text-xs shadow-md transition-all disabled:opacity-50"
              >
                {promoting ? 'Promoting...' : `Promote ${job.candidate_model_version} to Production`}
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/[0.08] flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-1 text-[11px]">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Promotion requires human sign-off by policy</span>
          </div>

          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
