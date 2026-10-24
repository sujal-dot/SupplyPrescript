import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DecisionROI from '../pages/DecisionROI';
import * as roiService from '../services/roiService';

vi.mock('../services/roiService');

// Mock ResizeObserver for Recharts ResponsiveContainer
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

describe('Decision ROI Dashboard (Day 21 Frontend)', () => {
  const mockDashboardData = {
    currency: 'USD',
    calculation_version: '1.0',
    summary: {
      total_decisions: 12,
      completed_decisions: 8,
      pending_decisions: 4,
      successful_decisions: 6,
      partially_successful_decisions: 1,
      failed_decisions: 1,
      eligible_completed_decisions: 8,
      success_rate: 75.0,
      partial_success_rate: 12.5,
      failure_rate: 12.5,
      average_cost_difference: '-450.00',
      average_cost_variance_percentage: -3.8,
      total_predicted_cost: '95000.00',
      total_actual_cost: '91400.00',
      forecast_variance: '3600.00',
      verified_baseline_savings: '14200.00',
      aggregate_roi: {
        investment_cost: '8000.00',
        net_benefit: '14200.00',
        roi_percentage: 177.5,
        status: 'CALCULATED',
        reason: 'Portfolio ROI weighted across 8 completed decisions.',
      },
      currency: 'USD',
    },
    prediction_accuracy: {
      cost_mae: 350.0,
      cost_mape: 3.2,
      cost_rmse: 480.0,
      cost_mean_signed_error: -450.0,
      cost_records_evaluated: 8,
      delay_mae_days: 0.65,
      delay_mean_error_days: -0.25,
      delay_records_evaluated: 8,
    },
    success_breakdown: [
      {
        status: 'SUCCESS',
        label: 'Successful',
        count: 6,
        percentage_of_eligible: 75.0,
        percentage_of_total: 50.0,
        color: '#10b981',
        description: 'Outcome cost <= +5%, delay <= 0.5 days, and all operational constraints satisfied.',
      },
      {
        status: 'PARTIAL_SUCCESS',
        label: 'Partially Successful',
        count: 1,
        percentage_of_eligible: 12.5,
        percentage_of_total: 8.3,
        color: '#f59e0b',
        description: 'Fulfillable with minor trade-off.',
      },
      {
        status: 'FAILURE',
        label: 'Failed',
        count: 1,
        percentage_of_eligible: 12.5,
        percentage_of_total: 8.3,
        color: '#ef4444',
        description: 'Outcome experienced severe cost overrun or delay.',
      },
      {
        status: 'PENDING_REVIEW',
        label: 'Pending Review',
        count: 4,
        percentage_of_eligible: null,
        percentage_of_total: 33.3,
        color: '#64748b',
        description: 'Operational execution in progress.',
      },
    ],
    cost_difference_by_strategy: [
      {
        strategy: 'AIR_FREIGHT',
        count: 5,
        average_cost_difference: '-800.00',
        total_predicted_cost: '60000.00',
        total_actual_cost: '56000.00',
      },
      {
        strategy: 'SECONDARY_SUPPLIER',
        count: 3,
        average_cost_difference: '+350.00',
        total_predicted_cost: '35000.00',
        total_actual_cost: '35400.00',
      },
    ],
    roi_by_strategy: [
      {
        strategy: 'AIR_FREIGHT',
        total_decisions: 7,
        completed_decisions: 5,
        successful_decisions: 5,
        success_rate: 100.0,
        average_cost_difference: '-800.00',
        verified_baseline_savings: '12000.00',
        total_investment_cost: '5000.00',
        total_net_benefit: '12000.00',
        roi_percentage: 240.0,
        roi_status: 'CALCULATED',
        roi_reason: 'Strategy weighted ROI: (12,000 USD net benefit / 5,000 USD investment) * 100.',
      },
      {
        strategy: 'SECONDARY_SUPPLIER',
        total_decisions: 5,
        completed_decisions: 3,
        successful_decisions: 1,
        success_rate: 33.3,
        average_cost_difference: '+350.00',
        verified_baseline_savings: '2200.00',
        total_investment_cost: '3000.00',
        total_net_benefit: '2200.00',
        roi_percentage: 73.3,
        roi_status: 'CALCULATED',
        roi_reason: 'Strategy weighted ROI: (2,200 USD net benefit / 3,000 USD investment) * 100.',
      },
    ],
    savings_timeline: [
      {
        date: '2026-10-18',
        forecast_variance: 1500.0,
        cumulative_forecast_variance: 1500.0,
        verified_baseline_savings: 5000.0,
        cumulative_baseline_savings: 5000.0,
        decision_count: 3,
      },
      {
        date: '2026-10-22',
        forecast_variance: 2100.0,
        cumulative_forecast_variance: 3600.0,
        verified_baseline_savings: 9200.0,
        cumulative_baseline_savings: 14200.0,
        decision_count: 5,
      },
    ],
    performance_table: {
      items: [
        {
          decision_id: 'DEC-20261022-001',
          db_id: 1,
          shipment_id: 'SHIP000005',
          strategy: 'AIR_FREIGHT',
          decision_name: 'Option A: Air Freight',
          decision_time: '2026-10-22T10:00:00Z',
          status: 'RECORDED',
          evaluation_status: 'SUCCESS',
          currency: 'USD',
          predicted_cost: '12000.00',
          actual_cost: '11200.00',
          cost_difference: '-800.00',
          cost_variance_pct: -6.67,
          predicted_delay: 2.0,
          actual_delay: 1.5,
          delay_difference: -0.5,
          baseline_savings: '3500.00',
          roi_percentage: 233.3,
          roi_status: 'CALCULATED',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
    data_quality: {
      total_in_filter: 12,
      completed_with_valid_costs: 8,
      completed_with_valid_delays: 8,
      decisions_with_valid_baseline: 8,
      excluded_currency_mismatches: 0,
      excluded_missing_data: 4,
      calculation_version: '1.0',
      methodology_notes: [
        'Cost difference = actual_cost - predicted_cost (positive = overrun, negative = savings vs forecast).',
        'Success rate denominator strictly excludes pending review decisions.',
      ],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Decision ROI header and subtitle', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Decision ROI/i })).toBeInTheDocument();
      expect(screen.getByText(/Closed-Loop Phase 6/i)).toBeInTheDocument();
    });
  });

  it('renders ROISummaryCards with accurate metrics and rates', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getAllByText('12').length).toBeGreaterThanOrEqual(1); // total decisions
      expect(screen.getAllByText('8').length).toBeGreaterThanOrEqual(1);  // completed decisions
      expect(screen.getByText('75.0%')).toBeInTheDocument(); // success rate
      expect(screen.getByText('-$450.00')).toBeInTheDocument(); // avg cost difference
      expect(screen.getAllByText('$14,200.00').length).toBeGreaterThanOrEqual(1); // baseline savings
      expect(screen.getByText('+177.5%')).toBeInTheDocument(); // aggregate ROI
    });
  });

  it('renders Success vs Failure chart with categories and denominator description', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText(/Recommendation Success vs Failure/i)).toBeInTheDocument();
      expect(screen.getByText(/75.0% Success Rate/i)).toBeInTheDocument();
      expect(screen.getByText(/Success rate denominator = 8 completed decisions/i)).toBeInTheDocument();
    });
  });

  it('renders Prediction Accuracy metrics (MAE, MAPE, RMSE, Signed Bias)', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText(/Prediction Accuracy & Error Metrics/i)).toBeInTheDocument();
      expect(screen.getByText('$350.00')).toBeInTheDocument(); // Cost MAE
      expect(screen.getByText('3.2%')).toBeInTheDocument();    // Cost MAPE
      expect(screen.getByText('$480.00')).toBeInTheDocument(); // Cost RMSE
      expect(screen.getByText('0.65 d')).toBeInTheDocument();  // Delay MAE
    });
  });

  it('renders Cumulative Savings Timeline distinguishing forecast variance vs baseline savings', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText(/Cumulative Savings & Variance Analysis/i)).toBeInTheDocument();
      expect(screen.getByText(/Methodological Separation:/i)).toBeInTheDocument();
    });
  });

  it('renders Strategy ROI chart with percentages and strategy names', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText(/Return on Investment \(ROI\) by Strategy/i)).toBeInTheDocument();
      expect(screen.getAllByText(/AIR FREIGHT/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/SECONDARY SUPPLIER/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders Decision Performance Table with audit rows and badges', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText('DEC-20261022-001')).toBeInTheDocument();
      expect(screen.getByText('SHIP000005')).toBeInTheDocument();
      expect(screen.getByText('Decision Success')).toBeInTheDocument();
      expect(screen.getByText('$3,500.00')).toBeInTheDocument(); // baseline savings
      expect(screen.getByText('+233.3%')).toBeInTheDocument();    // ROI
    });
  });

  it('renders Data Completeness & Methodology section', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText(/Data Completeness & Calculation Methodology/i)).toBeInTheDocument();
      expect(screen.getByText(/Methodology v1.0/i)).toBeInTheDocument();
      expect(screen.getByText(/Cost difference = actual_cost - predicted_cost/i)).toBeInTheDocument();
    });
  });

  it('calls API with updated filters when strategy filter is changed', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue(mockDashboardData);

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText('ROI Analytics Filters')).toBeInTheDocument();
    });

    const strategySelect = screen.getByDisplayValue('All Strategies');
    fireEvent.change(strategySelect, { target: { value: 'AIR_FREIGHT' } });

    await waitFor(() => {
      expect(roiService.getDecisionROIAnalytics).toHaveBeenCalledWith(
        expect.objectContaining({ strategy: 'AIR_FREIGHT', page: 1 })
      );
    });
  });

  it('handles empty response gracefully without crashing', async () => {
    roiService.getDecisionROIAnalytics.mockResolvedValue({
      currency: 'USD',
      summary: {},
      prediction_accuracy: {},
      success_breakdown: [],
      cost_difference_by_strategy: [],
      roi_by_strategy: [],
      savings_timeline: [],
      performance_table: { items: [], total: 0, page: 1, page_size: 20, total_pages: 1 },
      data_quality: {},
    });

    render(<DecisionROI />);

    await waitFor(() => {
      expect(screen.getByText('No Decision Outcomes Found')).toBeInTheDocument();
      expect(screen.getByText('No Cost Variance Data')).toBeInTheDocument();
      expect(screen.getByText('No Accuracy Benchmarks')).toBeInTheDocument();
      expect(screen.getByText('No Savings Timeline Data')).toBeInTheDocument();
      expect(screen.getByText('No Strategy ROI Data')).toBeInTheDocument();
    });
  });
});
