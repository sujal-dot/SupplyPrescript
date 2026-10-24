import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import FeedbackPipeline from '../pages/FeedbackPipeline';
import FeedbackStatusBadge from '../components/feedback/FeedbackStatusBadge';
import * as feedbackService from '../services/feedbackService';

vi.mock('../services/feedbackService');

describe('Model Feedback & Continuous Learning Pipeline (Day 22 Frontend)', () => {
  const mockSummaryCounts = {
    total: 24,
    eligible: 18,
    pending_outcome: 4,
    excluded: 2,
    under_review: 0,
    mean_absolute_error: 0.85,
    mean_signed_error: 0.35,
  };

  const mockFeedbackItems = [
    {
      feedback_id: 'FB-001001',
      prediction_id: 'PRED-101',
      shipment_id: 'SHP-9001',
      decision_id: 'DEC-8001',
      predicted_delay: 2.5,
      actual_delay: 3.2,
      prediction_error: 0.7,
      absolute_error: 0.7,
      prediction_timestamp: '2026-10-20T10:00:00Z',
      outcome_timestamp: '2026-10-23T14:30:00Z',
      model_version: 'v1.0.0',
      feedback_status: 'ELIGIBLE',
      exclusion_reason: null,
      dataset_version: 'FB_DS_20261025_001',
      notes: null,
      created_at: '2026-10-25T08:00:00Z',
    },
    {
      feedback_id: 'FB-001002',
      prediction_id: 'PRED-102',
      shipment_id: 'SHP-9002',
      decision_id: 'DEC-8002',
      predicted_delay: 4.0,
      actual_delay: null,
      prediction_error: null,
      absolute_error: null,
      prediction_timestamp: '2026-10-22T09:00:00Z',
      outcome_timestamp: null,
      model_version: 'v1.0.0',
      feedback_status: 'PENDING_OUTCOME',
      exclusion_reason: null,
      dataset_version: 'FB_DS_20261025_001',
      notes: 'Shipment currently in transit',
      created_at: '2026-10-25T08:00:00Z',
    },
    {
      feedback_id: 'FB-001003',
      prediction_id: 'PRED-103',
      shipment_id: 'SHP-9003',
      decision_id: null,
      predicted_delay: 1.0,
      actual_delay: 105.0,
      prediction_error: null,
      absolute_error: null,
      prediction_timestamp: '2026-10-15T08:00:00Z',
      outcome_timestamp: '2026-10-24T12:00:00Z',
      model_version: 'v1.0.0',
      feedback_status: 'EXCLUDED',
      exclusion_reason: 'Actual delivery delay exceeds anomaly threshold (>90 days)',
      dataset_version: 'FB_DS_20261025_001',
      notes: null,
      created_at: '2026-10-25T08:00:00Z',
    },
  ];

  const mockFeedbackListResponse = {
    items: mockFeedbackItems,
    total: 3,
    page: 1,
    page_size: 20,
    total_pages: 1,
    summary_counts: mockSummaryCounts,
  };

  const mockEvaluationResponse = {
    model_version: 'v1.0.0',
    dataset_version: null,
    status: 'EVALUATED',
    evaluated_count: 18,
    mae: 0.85,
    rmse: 1.12,
    mean_signed_error: 0.35,
    median_absolute_error: 0.70,
    min_error: -1.2,
    max_error: 2.4,
    is_preliminary: false,
    warnings: [],
    interpretation: 'Model v1.0.0 exhibits moderate accuracy with slight tendency to underestimate delay by +0.35 days.',
    error_sign_convention: 'prediction_error = actual_delay - predicted_delay',
    evaluation_timestamp: '2026-10-25T08:30:00Z',
  };

  const mockDatasets = [
    {
      dataset_version: 'FB_DS_20261025_001',
      created_at: '2026-10-25T08:00:00Z',
      schema_version: '1.0',
      row_count: 24,
      eligible_count: 18,
      excluded_count: 2,
      pending_count: 4,
      model_versions: ['v1.0.0'],
      source_predictions: ['PRED-101', 'PRED-102'],
      eligibility_rules: ['Rule 1', 'Rule 2'],
      metrics_summary: { mae: 0.85 },
      checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    feedbackService.getFeedbackList.mockResolvedValue(mockFeedbackListResponse);
    feedbackService.evaluateModel.mockResolvedValue(mockEvaluationResponse);
    feedbackService.getDatasetManifests.mockResolvedValue(mockDatasets);
    feedbackService.generateFeedback.mockResolvedValue({
      processed_count: 24,
      eligible_count: 18,
      pending_count: 4,
      excluded_count: 2,
      updated_count: 3,
      dataset_version: 'FB_DS_20261025_002',
      manifest_path: 'data/feedback/manifests/FB_DS_20261025_002.json',
      export_path: 'data/feedback/exports/FB_DS_20261025_002.csv',
      message: 'Feedback pipeline executed successfully',
    });
    feedbackService.formatApiError.mockImplementation((err) => err?.message || 'API error');
  });

  it('renders Feedback Pipeline page with title, KPI cards, and evaluation metrics', async () => {
    render(<FeedbackPipeline />);

    // Page title and subtitle
    expect(screen.getByText('Model Feedback & Continuous Learning')).toBeInTheDocument();
    expect(screen.getByText('Phase 7')).toBeInTheDocument();

    await waitFor(() => {
      // Summary cards KPIs
      expect(screen.getAllByText('24').length).toBeGreaterThanOrEqual(1); // total predictions
      expect(screen.getAllByText('18').length).toBeGreaterThanOrEqual(1); // eligible
      expect(screen.getAllByText('4').length).toBeGreaterThanOrEqual(1); // pending
      expect(screen.getAllByText('2').length).toBeGreaterThanOrEqual(1); // excluded
      expect(screen.getAllByText('0.85 d').length).toBeGreaterThanOrEqual(1); // Delay MAE
      expect(screen.getAllByText('+0.35 d').length).toBeGreaterThanOrEqual(1); // Directional bias
    });

    // Model Evaluation Panel
    expect(screen.getByText('Continuous Model Evaluation & Drift Diagnostics')).toBeInTheDocument();
    expect(screen.getByText('Evaluation Complete')).toBeInTheDocument();
    expect(screen.getByText('1.12 d')).toBeInTheDocument(); // RMSE
    expect(screen.getByText('0.70 d')).toBeInTheDocument(); // Median AE
    expect(
      screen.getByText(/Model v1.0.0 exhibits moderate accuracy with slight tendency/i)
    ).toBeInTheDocument();

    // Table rows
    expect(screen.getByText('FB-001001')).toBeInTheDocument();
    expect(screen.getByText('SHP-9001')).toBeInTheDocument();
    expect(screen.getByText('+0.7 d')).toBeInTheDocument(); // error
    expect(screen.getByText('Pending')).toBeInTheDocument(); // pending actual
    expect(
      screen.getByText(/Actual delivery delay exceeds anomaly threshold/i)
    ).toBeInTheDocument();

    // Dataset history
    expect(screen.getByText('FB_DS_20261025_001')).toBeInTheDocument();
    expect(screen.getByText('e3b0c44298fc...')).toBeInTheDocument();
  });

  it('triggers manual model evaluation on submit', async () => {
    render(<FeedbackPipeline />);

    await waitFor(() => {
      expect(screen.getByText('Evaluation Complete')).toBeInTheDocument();
    });

    const evaluateButton = screen.getByRole('button', { name: /evaluate/i });
    fireEvent.click(evaluateButton);

    await waitFor(() => {
      expect(feedbackService.evaluateModel).toHaveBeenCalledWith({
        model_version: 'v1.0.0',
        dataset_version: null,
        min_sample_threshold: 10,
      });
    });
  });

  it('triggers Generate Feedback pipeline snapshot on button click', async () => {
    render(<FeedbackPipeline />);

    const generateBtn = screen.getByRole('button', { name: /generate feedback snapshot/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(feedbackService.generateFeedback).toHaveBeenCalledWith({
        export_dataset: true,
        force_refresh: true,
      });
      expect(
        screen.getByText(/Feedback Pipeline executed: 24 pairs evaluated/i)
      ).toBeInTheDocument();
    });
  });

  it('filters feedback items by status and model version', async () => {
    render(<FeedbackPipeline />);

    await waitFor(() => {
      expect(screen.getByText('FB-001001')).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText(/filter by eligibility status/i);
    fireEvent.change(statusSelect, { target: { value: 'ELIGIBLE' } });

    await waitFor(() => {
      expect(feedbackService.getFeedbackList).toHaveBeenCalledWith(
        expect.objectContaining({
          feedback_status: 'ELIGIBLE',
        })
      );
    });
  });

  it('applies dataset filter when clicking Filter by DS in dataset history card', async () => {
    render(<FeedbackPipeline />);

    await waitFor(() => {
      expect(screen.getByText('FB_DS_20261025_001')).toBeInTheDocument();
    });

    const filterDsButton = screen.getByRole('button', { name: /filter by ds/i });
    fireEvent.click(filterDsButton);

    await waitFor(() => {
      expect(feedbackService.getFeedbackList).toHaveBeenCalledWith(
        expect.objectContaining({
          dataset_version: 'FB_DS_20261025_001',
        })
      );
    });
  });

  it('renders FeedbackStatusBadge correctly for all states', () => {
    const { rerender } = render(<FeedbackStatusBadge status="ELIGIBLE" />);
    expect(screen.getByText('Eligible')).toBeInTheDocument();

    rerender(<FeedbackStatusBadge status="PENDING_OUTCOME" />);
    expect(screen.getByText('Pending Outcome')).toBeInTheDocument();

    rerender(<FeedbackStatusBadge status="EXCLUDED" />);
    expect(screen.getByText('Excluded')).toBeInTheDocument();

    rerender(<FeedbackStatusBadge status="UNDER_REVIEW" />);
    expect(screen.getByText('Under Review')).toBeInTheDocument();
  });
});
