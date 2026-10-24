import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DecisionROISummary from '../components/roi/DecisionROISummary';
import DecisionROICards from '../components/roi/DecisionROICards';
import CostVarianceCard from '../components/roi/CostVarianceCard';
import DeliveryVarianceCard from '../components/roi/DeliveryVarianceCard';
import DecisionSuccessBadge from '../components/roi/DecisionSuccessBadge';
import ROIBreakdown from '../components/roi/ROIBreakdown';
import DecisionROITable from '../components/roi/DecisionROITable';
import DecisionDetailModal from '../components/dashboard/DecisionDetailModal';
import * as decisionService from '../services/decisionService';

vi.mock('../services/decisionService');

describe('Decision ROI Engine (Day 20 Frontend Tests)', () => {
  const mockROICompleted = {
    decision_id: 'DEC-EXEC-101',
    shipment_id: 'SHP-9001',
    currency: 'USD',
    cost: {
      predicted_cost: '15000.00',
      actual_cost: '18000.00',
      cost_difference: '3000.00',
      cost_variance_percentage: 20.0,
      money_saved_vs_prediction: '-3000.00',
      baseline_cost: '22000.00',
      money_saved_vs_baseline: '4000.00',
    },
    delivery: {
      predicted_delay: 3.0,
      actual_delay: 2.0,
      delay_difference: -1.0,
    },
    roi: {
      investment_cost: '2000.00',
      net_benefit: '4000.00',
      roi_percentage: 200.0,
      status: 'CALCULATED',
      reason: 'Calculated as (Net Benefit 4,000.00 USD / Incremental Investment 2,000.00 USD) * 100.',
    },
    decision_evaluation: {
      decision_success: 'PARTIAL_SUCCESS',
      cost_performance: 'WORSE_THAN_PREDICTED',
      delivery_performance: 'BETTER_THAN_PREDICTED',
      constraint_compliance: 'PASS',
      quantity_performance: 'MET_TARGET',
      data_completeness: 'COMPLETE',
      success_reason: 'Cost exceeded prediction while delivery was earlier than predicted; critical schedule milestone met.',
      policy_is_provisional: true,
    },
    calculation_version: '1.0',
    notes: ['Accounting calculation verified against PostgreSQL audit.'],
  };

  const mockROIPending = {
    decision_id: 'DEC-EXEC-102',
    shipment_id: 'SHP-9002',
    currency: 'USD',
    cost: {
      predicted_cost: '10000.00',
      actual_cost: null,
      cost_difference: null,
      cost_variance_percentage: null,
      money_saved_vs_prediction: null,
      baseline_cost: null,
      money_saved_vs_baseline: null,
    },
    delivery: {
      predicted_delay: 2.0,
      actual_delay: null,
      delay_difference: null,
    },
    roi: {
      investment_cost: null,
      net_benefit: null,
      roi_percentage: null,
      status: 'UNAVAILABLE',
      reason: 'A valid baseline and investment-cost definition are not available.',
    },
    decision_evaluation: {
      decision_success: 'PENDING_REVIEW',
      cost_performance: 'UNKNOWN',
      delivery_performance: 'UNKNOWN',
      constraint_compliance: 'PASS',
      quantity_performance: 'UNKNOWN',
      data_completeness: 'INSUFFICIENT',
      success_reason: 'Insufficient outcome data: actual cost and delivery outcomes are not yet recorded.',
      policy_is_provisional: true,
    },
    calculation_version: '1.0',
    notes: ['No operational outcome recorded for this decision; actual metrics are unavailable.'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('Requirement 1: renders ROI cards with backend-provided values', () => {
    render(<DecisionROICards roiData={mockROICompleted} />);

    expect(screen.getByText('$15,000.00')).toBeInTheDocument();
    expect(screen.getByText('$18,000.00')).toBeInTheDocument();
    expect(screen.getByText('+$3,000.00')).toBeInTheDocument();
    expect(screen.getByText('+200%')).toBeInTheDocument();
  });

  it('Requirement 2: labels positive and negative cost variances correctly', () => {
    // Overrun test
    const { rerender } = render(<CostVarianceCard cost={mockROICompleted.cost} currency="USD" />);
    expect(screen.getByText(/Overrun \(\+20%\)/i)).toBeInTheDocument();
    expect(screen.getByText('-$3,000.00')).toBeInTheDocument(); // money saved vs prediction is negative
    expect(screen.getByText('+$4,000.00')).toBeInTheDocument(); // money saved vs baseline is positive

    // Savings test
    const savingsCost = {
      predicted_cost: '15000.00',
      actual_cost: '12000.00',
      cost_difference: '-3000.00',
      cost_variance_percentage: -20.0,
      money_saved_vs_prediction: '3000.00',
      baseline_cost: '15000.00',
      money_saved_vs_baseline: '3000.00',
    };
    rerender(<CostVarianceCard cost={savingsCost} currency="USD" />);
    expect(screen.getByText(/Under budget \(-20%\)/i)).toBeInTheDocument();
    expect(screen.getAllByText('+$3,000.00').length).toBeGreaterThanOrEqual(1);
  });

  it('Requirement 3: delay differences use documented sign convention (-1.0d = earlier)', () => {
    render(<DeliveryVarianceCard delivery={mockROICompleted.delivery} />);

    expect(screen.getByText(/Earlier than predicted \(-1d\)/i)).toBeInTheDocument();
    expect(screen.getByText(/3.0 days/i)).toBeInTheDocument();
    expect(screen.getByText(/2.0 days/i)).toBeInTheDocument();
  });

  it('Requirement 4: missing values show as unavailable / pending rather than zero', () => {
    render(<DecisionROICards roiData={mockROIPending} />);

    // Actual cost should be Pending actuals, not $0.00
    expect(screen.getByText(/Pending actuals/i)).toBeInTheDocument();
    expect(screen.queryByText('$0.00')).not.toBeInTheDocument();

    // Actual delay should be Pending delivery, not 0d
    expect(screen.getByText(/Pending delivery/i)).toBeInTheDocument();

    // ROI percentage should be N/A, not 0%
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('Requirement 5: ROI breakdown displays methodology explanation', () => {
    render(<ROIBreakdown roi={mockROICompleted.roi} currency="USD" />);

    expect(screen.getByText(/Calculated as \(Net Benefit 4,000.00 USD \/ Incremental Investment 2,000.00 USD\) \* 100/i)).toBeInTheDocument();
    expect(screen.getByText('+$4,000.00 USD')).toBeInTheDocument();
    expect(screen.getByText('+$2,000.00 USD')).toBeInTheDocument();
  });

  it('Requirement 6: pending outcomes are represented correctly with badge and reason', () => {
    render(<DecisionROISummary roiData={mockROIPending} />);

    expect(screen.getAllByText('Pending Outcome').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Insufficient outcome data: actual cost and delivery outcomes are not yet recorded/i)).toBeInTheDocument();
    expect(screen.getByText(/No operational outcome recorded for this decision/i)).toBeInTheDocument();
  });

  it('Requirement 7: displays comparison table with only supported parameters', () => {
    render(<DecisionROITable roiData={mockROICompleted} />);

    expect(screen.getByText('Financial Cost')).toBeInTheDocument();
    expect(screen.getByText('Delay Impact')).toBeInTheDocument();
    expect(screen.getByText('$15,000.00 USD')).toBeInTheDocument();
    expect(screen.getByText('$18,000.00 USD')).toBeInTheDocument();
  });

  it('Requirement 8: DecisionDetailModal switches to ROI tab and displays DecisionROISummary', async () => {
    decisionService.getDecisionById.mockResolvedValueOnce({
      decision_id: 'DEC-EXEC-101',
      shipment_id: 'SHP-9001',
      status: 'RECORDED',
      predicted_cost: '15000.00',
      predicted_delay: 3.0,
      strategy: 'AIR_FREIGHT',
    });
    decisionService.getOutcome.mockResolvedValueOnce({
      decision_id: 'DEC-EXEC-101',
      actual: { actual_cost: 18000.0 },
    });
    decisionService.getDecisionROI.mockResolvedValueOnce(mockROICompleted);

    render(
      <DecisionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        decisionId="DEC-EXEC-101"
        initialTab="roi"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Decision ROI Engine & Success Analytics')).toBeInTheDocument();
      expect(screen.getAllByText('Partial Success').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('+$3,000.00').length).toBeGreaterThanOrEqual(1);
    });
  });
});
