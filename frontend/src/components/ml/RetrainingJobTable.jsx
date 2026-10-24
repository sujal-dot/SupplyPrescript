import React, { useState } from 'react';
import {
  FileText,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowUpRight,
  Sliders,
  ShieldCheck,
} from 'lucide-react';

export default function RetrainingJobTable({
  jobs = [],
  total = 0,
  page = 1,
  pageSize = 20,
  totalPages = 1,
  selectedStatus = '',
  onStatusChange = () => {},
  searchTerm = '',
  onSearchChange = () => {},
  onPageChange = () => {},
  onSelectJob = () => {},
  onPromoteJob = () => {},
  loading = false,
  promotingJobId = null,
}) {
  const getStatusBadge = (status) => {
    const s = String(status || 'QUEUED').toUpperCase();
    const configs = {
      PROMOTED: {
        label: 'Promoted',
        bg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
        icon: CheckCircle2,
      },
      REGISTERED: {
        label: 'Registered',
        bg: 'bg-red-500/15 text-red-300 border-red-500/30',
        icon: ShieldCheck,
      },
      REJECTED: {
        label: 'Rejected',
        bg: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
        icon: XCircle,
      },
      FAILED: {
        label: 'Failed',
        bg: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
        icon: AlertTriangle,
      },
      RUNNING: {
        label: 'Running',
        bg: 'bg-violet-500/15 text-violet-300 border-violet-500/30 animate-pulse',
        icon: Clock,
      },
      EVALUATING: {
        label: 'Evaluating',
        bg: 'bg-rose-500/15 text-rose-300 border-rose-500/30 animate-pulse',
        icon: Sliders,
      },
      INSUFFICIENT_DATA: {
        label: 'Insufficient Data',
        bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
        icon: Clock,
      },
      QUEUED: {
        label: 'Queued',
        bg: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
        icon: Clock,
      },
    };

    const cfg = configs[s] || configs.QUEUED;
    const Icon = cfg.icon;

    return (
      <span className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold border ${cfg.bg}`}>
        <Icon className="h-3 w-3 flex-shrink-0" />
        <span>{cfg.label}</span>
      </span>
    );
  };

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden mb-6">
      {/* Table Header and Filters */}
      <div className="p-5 border-b border-white/[0.08] flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
            <FileText className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Model Retraining Jobs & Candidate Audit Trail
            </h3>
            <p className="text-xs text-slate-400">
              Execution history of performance monitoring triggers and candidate training pipelines
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative w-full sm:w-56">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search job ID, reason..."
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900/80 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 transition-colors"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-1.5">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={selectedStatus}
              onChange={(e) => onStatusChange(e.target.value)}
              aria-label="Filter Retraining Jobs by Status"
              className="bg-slate-900/80 border border-white/10 rounded-xl text-xs text-slate-300 py-1.5 px-2.5 focus:outline-none focus:border-red-500 transition-colors"
            >
              <option value="">All Statuses</option>
              <option value="REGISTERED">Registered</option>
              <option value="PROMOTED">Promoted</option>
              <option value="REJECTED">Rejected</option>
              <option value="RUNNING">Running</option>
              <option value="FAILED">Failed</option>
              <option value="INSUFFICIENT_DATA">Insufficient Data</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-white/[0.08] bg-white/[0.02] text-slate-400 font-medium">
              <th className="py-3 px-4">Job ID</th>
              <th className="py-3 px-3">Status</th>
              <th className="py-3 px-3">Parent Model</th>
              <th className="py-3 px-3">Candidate Model</th>
              <th className="py-3 px-4">Trigger Rationale</th>
              <th className="py-3 px-3">Started</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              <tr>
                <td colSpan="7" className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <Clock className="h-6 w-6 text-red-400 animate-spin" />
                    <span>Loading retraining jobs...</span>
                  </div>
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td colSpan="7" className="py-12 text-center text-slate-500">
                  <p className="text-sm font-medium text-slate-400">No retraining jobs found</p>
                  <p className="text-xs text-slate-600 max-w-sm mx-auto mt-1">
                    Retraining jobs are triggered when performance degradation is detected or initiated manually.
                  </p>
                </td>
              </tr>
            ) : (
              jobs.map((job) => {
                const isPromoting = promotingJobId === job.job_id;
                const canPromote = job.status === 'REGISTERED';
                const startDateStr = job.started_at ? new Date(job.started_at).toLocaleString() : '—';

                return (
                  <tr key={job.job_id} className="hover:bg-white/[0.02] transition-colors">
                    {/* Job ID */}
                    <td className="py-3 px-4 font-mono font-semibold text-white">
                      {job.job_id}
                    </td>

                    {/* Status Badge */}
                    <td className="py-3 px-3">
                      {getStatusBadge(job.status)}
                    </td>

                    {/* Parent Version */}
                    <td className="py-3 px-3 font-mono text-slate-300">
                      {job.parent_model_version}
                    </td>

                    {/* Candidate Version */}
                    <td className="py-3 px-3 font-mono">
                      {job.candidate_model_version ? (
                        <span className="text-red-300 font-semibold px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20">
                          {job.candidate_model_version}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    {/* Trigger Rationale */}
                    <td className="py-3 px-4 max-w-xs text-slate-300 truncate" title={job.trigger_reason}>
                      {job.trigger_reason}
                    </td>

                    {/* Started Date */}
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-400">
                      {startDateStr}
                    </td>

                    {/* Action buttons */}
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => onSelectJob(job)}
                          className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-[11px] font-medium transition-colors"
                        >
                          Details
                        </button>

                        {canPromote && (
                          <button
                            onClick={() => onPromoteJob(job.job_id)}
                            disabled={isPromoting}
                            className="px-2.5 py-1 rounded-lg bg-gradient-to-r from-emerald-600 to-red-600 hover:from-emerald-500 hover:to-red-500 text-white text-[11px] font-bold shadow-sm transition-all disabled:opacity-50"
                          >
                            {isPromoting ? 'Promoting...' : 'Promote'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
        <div>
          Showing <span className="font-semibold text-white">{total > 0 ? (page - 1) * pageSize + 1 : 0}</span> to{' '}
          <span className="font-semibold text-white">{Math.min(page * pageSize, total)}</span> of{' '}
          <span className="font-semibold text-white">{total.toLocaleString()}</span> jobs
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || loading}
            aria-label="Previous Jobs Page"
            className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="font-mono px-2 py-1 text-slate-300">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
            aria-label="Next Jobs Page"
            className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
