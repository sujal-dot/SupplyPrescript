import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Database,
  SlidersHorizontal,
  Info,
  BookOpen,
  Cpu,
  Play,
  RotateCcw,
  Layers,
} from 'lucide-react';
import GlassButton from '../components/ui/GlassButton';
import FeedbackSummaryCards from '../components/feedback/FeedbackSummaryCards';
import ModelEvaluationPanel from '../components/feedback/ModelEvaluationPanel';
import PredictionErrorTable from '../components/feedback/PredictionErrorTable';
import FeedbackDatasetHistory from '../components/feedback/FeedbackDatasetHistory';
import RetrainingStatusCards from '../components/ml/RetrainingStatusCards';
import RetrainingJobTable from '../components/ml/RetrainingJobTable';
import RetrainingJobDetailsModal from '../components/ml/RetrainingJobDetailsModal';
import {
  generateFeedback,
  getFeedbackList,
  evaluateModel,
  getDatasetManifests,
  formatApiError,
} from '../services/feedbackService';
import {
  getRetrainingMonitorStatus,
  runRetrainingJob,
  getRetrainingJobs,
  promoteCandidateModel,
  rollbackModelVersion,
} from '../services/retrainingService';

export default function FeedbackPipeline() {
  const [activeTab, setActiveTab] = useState('feedback'); // 'feedback' | 'retraining'

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [retrainingRunning, setRetrainingRunning] = useState(false);
  const [promotingJobId, setPromotingJobId] = useState(null);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Day 22 Feedback Data states
  const [feedbackData, setFeedbackData] = useState({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 1,
    summary_counts: {},
  });
  const [datasets, setDatasets] = useState([]);
  const [evaluationResult, setEvaluationResult] = useState(null);

  // Day 23 Retraining states
  const [monitorStatus, setMonitorStatus] = useState(null);
  const [retrainingJobsData, setRetrainingJobsData] = useState({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 1,
  });
  const [selectedJob, setSelectedJob] = useState(null);
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [jobStatusFilter, setJobStatusFilter] = useState('');
  const [jobSearchTerm, setJobSearchTerm] = useState('');
  const [jobCurrentPage, setJobCurrentPage] = useState(1);
  const [forceRetrain, setForceRetrain] = useState(false);

  // Filter states for feedback
  const [currentPage, setCurrentPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [modelVersionFilter, setModelVersionFilter] = useState('');
  const [datasetFilter, setDatasetFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch feedback records and summary
  const fetchFeedbackData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        page: currentPage,
        page_size: 20,
        feedback_status: statusFilter || undefined,
        model_version: modelVersionFilter || undefined,
        dataset_version: datasetFilter || undefined,
        shipment_id: searchTerm ? searchTerm.trim() : undefined,
      };

      const res = await getFeedbackList(params);
      setFeedbackData(res);
    } catch (err) {
      console.error('Failed to load feedback records:', err);
      setError(formatApiError(err) || 'Failed to fetch feedback records');
    } finally {
      setLoading(false);
    }
  }, [currentPage, statusFilter, modelVersionFilter, datasetFilter, searchTerm]);

  // Fetch dataset manifests
  const fetchDatasets = useCallback(async () => {
    try {
      const manifests = await getDatasetManifests();
      setDatasets(Array.isArray(manifests) ? manifests : []);
    } catch (err) {
      console.warn('Failed to load dataset manifests:', err);
    }
  }, []);

  // Fetch Day 23 Retraining Monitor Status and Jobs
  const fetchRetrainingData = useCallback(async () => {
    try {
      const [monitorRes, jobsRes] = await Promise.all([
        getRetrainingMonitorStatus(),
        getRetrainingJobs({
          page: jobCurrentPage,
          page_size: 20,
          status: jobStatusFilter || undefined,
        }),
      ]);
      setMonitorStatus(monitorRes);
      setRetrainingJobsData(jobsRes);
    } catch (err) {
      console.warn('Failed to load retraining data:', err);
    }
  }, [jobCurrentPage, jobStatusFilter]);

  // Run initial evaluation for active model
  const runEvaluation = useCallback(
    async (params = { model_version: 'v1.0.0', min_sample_threshold: 10 }) => {
      try {
        setEvaluating(true);
        setError(null);
        const result = await evaluateModel(params);
        setEvaluationResult(result);
      } catch (err) {
        console.error('Evaluation failed:', err);
        setError(formatApiError(err) || 'Model evaluation failed');
      } finally {
        setEvaluating(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchFeedbackData();
    fetchDatasets();
    fetchRetrainingData();
  }, [fetchFeedbackData, fetchDatasets, fetchRetrainingData]);

  // Initial auto-evaluation on mount
  useEffect(() => {
    runEvaluation({ model_version: 'v1.0.0', min_sample_threshold: 10 });
  }, [runEvaluation]);

  // Handler to trigger feedback generation
  const handleGenerateFeedback = async () => {
    try {
      setGenerating(true);
      setError(null);
      setActionSuccess(null);

      const res = await generateFeedback({
        export_dataset: true,
        force_refresh: true,
      });

      setActionSuccess(
        `Feedback Pipeline executed: ${res.processed_count} pairs evaluated (${res.eligible_count} eligible, ${res.pending_count} pending, ${res.excluded_count} excluded). Dataset ${res.dataset_version || ''} snapshot created.`
      );

      // Refresh all data
      await Promise.all([
        fetchFeedbackData(),
        fetchDatasets(),
        fetchRetrainingData(),
        runEvaluation({ model_version: 'v1.0.0' }),
      ]);
    } catch (err) {
      console.error('Feedback generation failed:', err);
      setError(formatApiError(err) || 'Failed to generate feedback observations');
    } finally {
      setGenerating(false);
    }
  };

  // Handler to run or evaluate retraining
  const handleTriggerRetraining = async () => {
    try {
      setRetrainingRunning(true);
      setError(null);
      setActionSuccess(null);

      const res = await runRetrainingJob({
        trigger_reason: forceRetrain ? 'Manual forced retraining run' : 'Operator degradation evaluation',
        force: forceRetrain,
      });

      if (res.status === 'INSUFFICIENT_DATA' || res.status === 'HEALTHY' || res.status === 'BLOCKED') {
        setActionSuccess(`Retraining evaluation: ${res.message}`);
      } else {
        setActionSuccess(`Retraining Job ${res.job_id} completed with status: ${res.status}. Candidate: ${res.candidate_version || 'None'}`);
      }

      await fetchRetrainingData();
    } catch (err) {
      console.error('Retraining execution failed:', err);
      setError(formatApiError(err) || 'Failed to initiate retraining run');
    } finally {
      setRetrainingRunning(false);
    }
  };

  // Handler to promote candidate
  const handlePromoteCandidate = async (jobId) => {
    try {
      setPromotingJobId(jobId);
      setError(null);
      setActionSuccess(null);

      const res = await promoteCandidateModel(jobId);
      setActionSuccess(`Successfully promoted candidate model version ${res.promoted_version} to active production!`);

      if (isJobModalOpen) setIsJobModalOpen(false);
      await fetchRetrainingData();
    } catch (err) {
      console.error('Promotion failed:', err);
      setError(formatApiError(err) || 'Candidate promotion failed');
    } finally {
      setPromotingJobId(null);
    }
  };

  // Handler to roll back model
  const handleRollback = async (targetVersion = 'v1.0') => {
    try {
      setError(null);
      setActionSuccess(null);

      const res = await rollbackModelVersion(targetVersion);
      setActionSuccess(`Production model safely rolled back from ${res.rolled_back_from} to ${res.active_version}.`);

      await fetchRetrainingData();
    } catch (err) {
      console.error('Rollback failed:', err);
      setError(formatApiError(err) || 'Model rollback failed');
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-black text-white tracking-tight">
              Model Feedback & Continuous Learning
            </h1>
            <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30 font-semibold">
              Phase 7
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Ground-truth error feedback, drift diagnostics, and monitored XGBoost candidate retraining with independent validation.
          </p>
        </div>

        {/* Global Pipeline Action Buttons */}
        <div className="flex items-center space-x-3">
          <GlassButton
            onClick={() => {
              fetchFeedbackData();
              fetchDatasets();
              fetchRetrainingData();
            }}
            disabled={loading || generating || retrainingRunning}
            className="flex items-center space-x-2 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </GlassButton>

          {activeTab === 'feedback' ? (
            <button
              onClick={handleGenerateFeedback}
              disabled={generating}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold shadow-lg shadow-red-500/20 disabled:opacity-50 transition-all"
            >
              <Sparkles className={`h-3.5 w-3.5 ${generating ? 'animate-spin' : ''}`} />
              <span>{generating ? 'Scanning Outcomes...' : 'Generate Feedback Snapshot'}</span>
            </button>
          ) : (
            <div className="flex items-center space-x-2">
              <label className="flex items-center space-x-1.5 text-xs text-slate-400 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={forceRetrain}
                  onChange={(e) => setForceRetrain(e.target.checked)}
                  className="rounded bg-slate-900 border-white/20 text-red-500 focus:ring-0"
                />
                <span>Force Retrain</span>
              </label>

              <button
                onClick={handleTriggerRetraining}
                disabled={retrainingRunning}
                className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-red-600 hover:from-violet-500 hover:to-red-500 text-white text-xs font-bold shadow-lg shadow-violet-500/20 disabled:opacity-50 transition-all"
              >
                <Cpu className={`h-3.5 w-3.5 ${retrainingRunning ? 'animate-spin' : ''}`} />
                <span>{retrainingRunning ? 'Running Pipeline...' : 'Run Retraining Pipeline'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tab Navigation Pill Bar */}
      <div className="flex items-center space-x-2 border-b border-white/[0.08] pb-3">
        <button
          onClick={() => setActiveTab('feedback')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'feedback'
              ? 'bg-red-500/20 text-red-300 border border-red-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Sparkles className="h-4 w-4" />
          <span>Prediction Errors & Feedback (Day 22)</span>
        </button>

        <button
          onClick={() => setActiveTab('retraining')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'retraining'
              ? 'bg-violet-500/20 text-violet-300 border border-violet-400/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Cpu className="h-4 w-4" />
          <span>Automated Retraining & Candidate Monitor (Day 23)</span>
        </button>
      </div>

      {/* Action Success Alert */}
      {actionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-emerald-400 hover:text-white text-xs font-mono px-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-rose-400 hover:text-white text-xs font-mono px-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* TAB 1: Day 22 Feedback & Evaluation */}
      {activeTab === 'feedback' && (
        <>
          {/* Summary KPI Cards */}
          <FeedbackSummaryCards
            summary={feedbackData.summary_counts}
            activeModelVersion="v1.0.0"
            datasetVersion={datasetFilter || (datasets.length > 0 ? datasets[0].dataset_version : null)}
            loading={loading && !feedbackData.items.length}
          />

          {/* Model Evaluation Panel */}
          <ModelEvaluationPanel
            evaluationResult={evaluationResult}
            onEvaluate={runEvaluation}
            loading={evaluating}
            datasetVersions={datasets}
          />

          {/* Prediction Error Observation Table */}
          <PredictionErrorTable
            feedbackData={feedbackData}
            selectedStatus={statusFilter}
            onStatusChange={(val) => {
              setStatusFilter(val);
              setCurrentPage(1);
            }}
            selectedModelVersion={modelVersionFilter}
            onModelVersionChange={(val) => {
              setModelVersionFilter(val);
              setCurrentPage(1);
            }}
            searchTerm={searchTerm}
            onSearchChange={(val) => {
              setSearchTerm(val);
              setCurrentPage(1);
            }}
            currentPage={currentPage}
            onPageChange={(p) => setCurrentPage(p)}
            loading={loading}
          />

          {/* Feedback Dataset Manifests History */}
          <FeedbackDatasetHistory
            datasets={datasets}
            activeDatasetFilter={datasetFilter}
            onSelectDataset={(ver) => {
              setDatasetFilter(ver);
              setCurrentPage(1);
            }}
            loading={loading && !datasets.length}
          />
        </>
      )}

      {/* TAB 2: Day 23 Retraining & Candidate Monitor */}
      {activeTab === 'retraining' && (
        <>
          {/* Retraining Status KPI Cards */}
          <RetrainingStatusCards
            monitorStatus={monitorStatus}
            loading={!monitorStatus}
          />

          {/* Retraining Jobs Audit Table */}
          <RetrainingJobTable
            jobs={retrainingJobsData.items}
            total={retrainingJobsData.total}
            page={retrainingJobsData.page}
            pageSize={retrainingJobsData.page_size}
            totalPages={retrainingJobsData.total_pages}
            selectedStatus={jobStatusFilter}
            onStatusChange={(s) => {
              setJobStatusFilter(s);
              setJobCurrentPage(1);
            }}
            searchTerm={jobSearchTerm}
            onSearchChange={setJobSearchTerm}
            onPageChange={setJobCurrentPage}
            onSelectJob={(job) => {
              setSelectedJob(job);
              setIsJobModalOpen(true);
            }}
            onPromoteJob={handlePromoteCandidate}
            promotingJobId={promotingJobId}
          />

          {/* Production Rollback Section */}
          <div className="glass-card p-5 rounded-2xl border border-white/[0.08] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300">
                <RotateCcw className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white tracking-tight">
                  Emergency Production Rollback Safeguard
                </h4>
                <p className="text-xs text-slate-400">
                  Restore the canonical active production model to baseline v1.0 without deleting candidate reports
                </p>
              </div>
            </div>

            <button
              onClick={() => handleRollback('v1.0')}
              className="px-4 py-2 rounded-xl bg-amber-500/15 border border-amber-500/30 hover:bg-amber-500/25 text-amber-300 text-xs font-bold transition-all"
            >
              Roll Back to v1.0
            </button>
          </div>
        </>
      )}

      {/* Retraining Job Details Modal */}
      <RetrainingJobDetailsModal
        job={selectedJob}
        isOpen={isJobModalOpen}
        onClose={() => {
          setIsJobModalOpen(false);
          setSelectedJob(null);
        }}
        onPromote={handlePromoteCandidate}
        promoting={promotingJobId === selectedJob?.job_id}
      />

      {/* Governance & Retraining Policy Section */}
      <div className="glass-card p-5 rounded-2xl border border-white/[0.08] text-xs text-slate-400 space-y-3">
        <div className="flex items-center space-x-2 text-white font-bold text-sm">
          <BookOpen className="h-4 w-4 text-red-400" />
          <span>Day 23 Monitored Retraining Architecture & Safety Invariants</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05]">
            <div className="font-semibold text-slate-200 mb-1">Target & Feature Preservation</div>
            <div className="font-mono text-[11px] text-red-300 mb-1">
              delay_days (reg) &amp; delayed (cls)
            </div>
            <p className="text-[11px] leading-relaxed">
              Retraining strictly preserves established Day 6 target definitions. Candidates are NEVER trained directly on <span className="font-mono text-slate-300">prediction_error</span>. All 11 approved features are validated against leakage.
            </p>
          </div>

          <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05]">
            <div className="font-semibold text-slate-200 mb-1">Empirical Acceptance Criteria</div>
            <div className="font-mono text-[11px] text-emerald-300 mb-1">
              MAE improvement &gt;= 3% | RMSE &lt;= 10%
            </div>
            <p className="text-[11px] leading-relaxed">
              Candidates are evaluated on an identical untouched holdout dataset. A model is never promoted merely because it is newer; it must demonstrably outperform the active baseline.
            </p>
          </div>

          <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05]">
            <div className="font-semibold text-slate-200 mb-1">Controlled Promotion &amp; Rollback</div>
            <div className="font-mono text-[11px] text-violet-300 mb-1">
              atomic pointer &amp; instant rollback
            </div>
            <p className="text-[11px] leading-relaxed">
              Candidate artifacts are stored in isolated directories without touching production. Promotion is atomic via <span className="font-mono text-slate-300">active.json</span> and PostgreSQL, with instant rollback to v1.0 supported.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
