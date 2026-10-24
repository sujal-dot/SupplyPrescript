import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RetrainingStatusCards from '../components/ml/RetrainingStatusCards';
import CandidateValidationReport from '../components/ml/CandidateValidationReport';
import RetrainingJobTable from '../components/ml/RetrainingJobTable';
import RetrainingJobDetailsModal from '../components/ml/RetrainingJobDetailsModal';
import FeedbackPipeline from '../pages/FeedbackPipeline';
import * as retrainingService from '../services/retrainingService';
import * as feedbackService from '../services/feedbackService';

vi.mock('../services/retrainingService');
vi.mock('../services/feedbackService');

describe('Automatic Retraining & Model Monitoring (Day 23 Frontend)', () => {
  const mockMonitorStatus = {
    status: 'INSUFFICIENT_DATA',
    is_degraded: false,
    model_version: 'v1.0',
    evaluated_sample_count: 3,
    min_sample_threshold: 10,
    trigger_reason: 'INSUFFICIENT_DATA: 3 verified feedback observations available; minimum threshold is 10.',
    current_metrics: {
      sample_count: 3,
      mae: 1.85,
      mae_delta: -0.19,
      mae_delta_pct: -9.2,
    },
    baseline_metrics: {
      mae: 2.04,
      rmse: 2.91,
    },
    thresholds_applied: {
      min_sample_threshold: 10,
      degradation_mae_threshold_pct: 15.0,
    },
    evaluation_timestamp: '2026-10-26T10:00:00Z',
  };

  const mockJobs = [
    {
      id: 1,
      job_id: 'RETRAIN_20261026_001',
      trigger_reason: 'PERFORMANCE_DEGRADATION: MAE increased by 18.5%',
      triggered_by: 'system_pipeline',
      model_name: 'supplyprescript_delay_engine',
      parent_model_version: 'v1.0',
      candidate_model_version: 'v1.1',
      dataset_version: 'FINGERPRINT_A1B2C3D4E5F6',
      status: 'REGISTERED',
      started_at: '2026-10-26T09:00:00Z',
      completed_at: '2026-10-26T09:05:00Z',
      baseline_metrics: { mae: 2.04, rmse: 2.91 },
      candidate_metrics: { candidate_mae: 1.75, baseline_mae: 2.04, mae_improvement_pct: 14.2 },
      acceptance_result: {
        accepted: true,
        recommendation: 'PROMOTE_ELIGIBLE',
        checks: {
          artifact_integrity: true,
          smoke_test_predictions: true,
          leakage_check: true,
          minimum_sample_size: true,
          mae_improvement: true,
          rmse_within_limit: true,
        },
        comparison: {
          candidate_mae: 1.75,
          baseline_mae: 2.04,
          mae_improvement_pct: 14.2,
          candidate_rmse: 2.65,
          baseline_rmse: 2.91,
          rmse_regression_pct: -8.9,
        },
        errors: [],
      },
    },
    {
      id: 2,
      job_id: 'RETRAIN_20261026_002',
      trigger_reason: 'Manual forced retraining run',
      triggered_by: 'operator_manual',
      model_name: 'supplyprescript_delay_engine',
      parent_model_version: 'v1.0',
      candidate_model_version: 'v1.2',
      dataset_version: 'FINGERPRINT_123456789ABC',
      status: 'REJECTED',
      started_at: '2026-10-26T10:00:00Z',
      completed_at: '2026-10-26T10:04:00Z',
      failure_reason: 'Candidate MAE (2.15d) regressed relative to baseline (2.04d).',
      acceptance_result: {
        accepted: false,
        recommendation: 'REJECT_CANDIDATE',
        checks: {
          artifact_integrity: true,
          smoke_test_predictions: true,
          leakage_check: true,
          mae_improvement: false,
        },
        comparison: {
          candidate_mae: 2.15,
          baseline_mae: 2.04,
          mae_improvement_pct: -5.4,
        },
        errors: ['Candidate MAE (2.15d) regressed relative to baseline (2.04d).'],
      },
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    retrainingService.getRetrainingMonitorStatus.mockResolvedValue(mockMonitorStatus);
    retrainingService.getRetrainingJobs.mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    retrainingService.runRetrainingJob.mockResolvedValue({
      status: 'INSUFFICIENT_DATA',
      message: 'INSUFFICIENT_DATA: 3 verified feedback observations available; minimum threshold is 10.',
    });
    retrainingService.promoteCandidateModel.mockResolvedValue({
      status: 'SUCCESS',
      promoted_version: 'v1.1',
      active_model_version: 'v1.1',
    });
    retrainingService.rollbackModelVersion.mockResolvedValue({
      status: 'SUCCESS',
      rolled_back_from: 'v1.1',
      active_version: 'v1.0',
    });

    feedbackService.getFeedbackList.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
      summary_counts: { total: 0, eligible: 0 },
    });
    feedbackService.getDatasetManifests.mockResolvedValue([]);
    feedbackService.evaluateModel.mockResolvedValue({ status: 'INSUFFICIENT_DATA' });
    feedbackService.formatApiError.mockImplementation((err) => err?.message || 'Error');
  });

  it('renders RetrainingStatusCards with active model and monitor status', () => {
    render(<RetrainingStatusCards monitorStatus={mockMonitorStatus} loading={false} />);

    expect(screen.getByText('Active Production Model')).toBeInTheDocument();
    expect(screen.getByText('v1.0')).toBeInTheDocument();
    expect(screen.getByText('Performance Drift Monitor')).toBeInTheDocument();
    expect(screen.getByText('Insufficient Data')).toBeInTheDocument();
    expect(screen.getByText('3 / 10 samples needed')).toBeInTheDocument();
  });

  it('renders CandidateValidationReport with benchmark metrics and acceptance decision', () => {
    const valResult = mockJobs[0].acceptance_result;
    render(
      <CandidateValidationReport
        validationResult={valResult}
        candidateVersion="v1.1"
        baselineVersion="v1.0"
      />
    );

    expect(screen.getByText('PROMOTE ELIGIBLE')).toBeInTheDocument();
    expect(screen.getByText('1.750 d')).toBeInTheDocument(); // Candidate MAE
    expect(screen.getByText('2.040 d')).toBeInTheDocument(); // Baseline MAE
    expect(screen.getByText('+14.2% vs baseline')).toBeInTheDocument();
    expect(screen.getByText('Artifact Integrity & SHA-256 Checksums')).toBeInTheDocument();
  });

  it('renders RetrainingJobTable and handles Details inspection and Promote clicks', () => {
    const handleSelect = vi.fn();
    const handlePromote = vi.fn();

    render(
      <RetrainingJobTable
        jobs={mockJobs}
        total={2}
        page={1}
        pageSize={20}
        totalPages={1}
        onSelectJob={handleSelect}
        onPromoteJob={handlePromote}
      />
    );

    expect(screen.getByText('RETRAIN_20261026_001')).toBeInTheDocument();
    expect(screen.getAllByText('Registered').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Rejected').length).toBeGreaterThanOrEqual(1);

    // Inspect button
    const detailButtons = screen.getAllByRole('button', { name: /details/i });
    fireEvent.click(detailButtons[0]);
    expect(handleSelect).toHaveBeenCalledWith(mockJobs[0]);

    // Promote button for REGISTERED job
    const promoteButton = screen.getByRole('button', { name: /^promote$/i });
    fireEvent.click(promoteButton);
    expect(handlePromote).toHaveBeenCalledWith('RETRAIN_20261026_001');
  });

  it('renders RetrainingJobDetailsModal and allows promotion of REGISTERED candidate', () => {
    const handlePromote = vi.fn();
    const handleClose = vi.fn();

    render(
      <RetrainingJobDetailsModal
        job={mockJobs[0]}
        isOpen={true}
        onClose={handleClose}
        onPromote={handlePromote}
      />
    );

    expect(screen.getByText('RETRAIN_20261026_001')).toBeInTheDocument();
    expect(screen.getByText('Approve Candidate Promotion')).toBeInTheDocument();

    const promoteSubmit = screen.getByRole('button', {
      name: /promote v1.1 to production/i,
    });
    fireEvent.click(promoteSubmit);
    expect(handlePromote).toHaveBeenCalledWith('RETRAIN_20261026_001');
  });

  it('switches to Retraining tab and triggers retraining run from FeedbackPipeline page', async () => {
    render(<FeedbackPipeline />);

    // Switch to Retraining tab
    const retrainingTabBtn = screen.getByRole('button', {
      name: /automated retraining & candidate monitor/i,
    });
    fireEvent.click(retrainingTabBtn);

    await waitFor(() => {
      expect(screen.getByText('Run Retraining Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Emergency Production Rollback Safeguard')).toBeInTheDocument();
    });

    // Click run retraining
    const runBtn = screen.getByRole('button', { name: /run retraining pipeline/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(retrainingService.runRetrainingJob).toHaveBeenCalledWith({
        trigger_reason: 'Operator degradation evaluation',
        force: false,
      });
    });
  });
});
