import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PredictedActualComparison from '../components/outcomes/PredictedActualComparison';
import OutcomeVarianceCards from '../components/outcomes/OutcomeVarianceCards';
import OutcomeEntryModal from '../components/outcomes/OutcomeEntryModal';
import DecisionDetailModal from '../components/dashboard/DecisionDetailModal';
import * as decisionService from '../services/decisionService';

describe('Closed-Loop Outcome Tracking (Day 19 Frontend)', () => {
  const mockComparison = {
    decision_id: 'DEC-20261022-0001',
    shipment_id: 'SHIP000005',
    predicted: {
      predicted_cost: 15000.0,
      predicted_delay: 1.0,
      predicted_delivery_date: '2026-10-10',
      planned_quantity: 500,
      planned_supplier: 'SUPPLIER_ORIGINAL',
      currency: 'USD',
    },
    actual: {
      outcome_id: 'OUT-20261022-0001',
      actual_cost: 16200.0,
      actual_delay: 2.0,
      actual_delivery_date: '2026-10-12',
      actual_quantity: 500,
      actual_supplier: 'SUPPLIER_EXPEDITED',
      currency: 'USD',
      outcome_status: 'DELIVERED',
      source: 'manual_entry',
      recorded_at: '2026-10-22T10:00:00Z',
    },
    variance: {
      cost_variance: 1200.0,
      cost_variance_percentage: 8.0,
      delay_variance: 1.0,
      delivery_date_variance_days: 2,
      quantity_variance: 0.0,
      supplier_matched: false,
    },
    data_completeness: 'COMPLETE',
    notes: ['Fuel surcharge applied.'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders PredictedActualComparison table and variance metrics accurately', () => {
    render(<PredictedActualComparison comparison={mockComparison} />);

    expect(screen.getByText('Closed-Loop Analytics: Predicted vs Actual Outcomes')).toBeInTheDocument();
    expect(screen.getByText('DEC-20261022-0001')).toBeInTheDocument();
    expect(screen.getByText('COMPLETE')).toBeInTheDocument();

    // Verify Cost row
    expect(screen.getByText('$15,000.00 USD')).toBeInTheDocument();
    expect(screen.getByText('$16,200.00 USD')).toBeInTheDocument();
    expect(screen.getAllByText(/\+8/i).length).toBeGreaterThanOrEqual(1);

    // Verify Supplier row
    expect(screen.getByText('SUPPLIER_ORIGINAL')).toBeInTheDocument();
    expect(screen.getByText('SUPPLIER_EXPEDITED')).toBeInTheDocument();
    expect(screen.getByText('Substituted Supplier')).toBeInTheDocument();

    // Verify Notes
    expect(screen.getByText('Fuel surcharge applied.')).toBeInTheDocument();
  });

  it('renders OutcomeVarianceCards with proper sign and direction styling', () => {
    render(
      <OutcomeVarianceCards
        variance={mockComparison.variance}
        predicted={mockComparison.predicted}
        actual={mockComparison.actual}
      />
    );

    // Cost variance card
    expect(screen.getByText('Cost Variance')).toBeInTheDocument();
    expect(screen.getByText('+$1,200.00')).toBeInTheDocument();
    expect(screen.getByText('+8%')).toBeInTheDocument();

    // Delay variance card
    expect(screen.getByText('Delay Variance')).toBeInTheDocument();
    expect(screen.getByText('+1.0 days')).toBeInTheDocument();
    expect(screen.getByText('Later than predicted')).toBeInTheDocument();
  });

  it('validates OutcomeEntryModal inputs and calls recordOutcome API on submit', async () => {
    const recordSpy = vi.spyOn(decisionService, 'recordOutcome').mockResolvedValue(mockComparison);
    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    render(
      <OutcomeEntryModal
        isOpen={true}
        onClose={handleClose}
        decision={{
          decision_id: 'DEC-20261022-0001',
          shipment_id: 'SHIP000005',
          predicted_cost: 15000.0,
          predicted_delay: 1.0,
        }}
        onSuccess={handleSuccess}
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Record Actual Operational Outcome')).toBeInTheDocument();

    // Fill in cost
    const costInput = screen.getByPlaceholderText('e.g. 16200.00');
    fireEvent.change(costInput, { target: { value: '16200.00' } });

    // Fill in delivery date
    const dateInputs = screen.getAllByDisplayValue('');
    const deliveryDateInput = document.querySelector('input[type="date"]');
    if (deliveryDateInput) {
      fireEvent.change(deliveryDateInput, { target: { value: '2026-10-12' } });
    }

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /Commit Actual Outcome/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(recordSpy).toHaveBeenCalledWith(
        'DEC-20261022-0001',
        expect.objectContaining({
          actual_cost: 16200.0,
          currency: 'USD',
          source: 'manual_entry',
        })
      );
    });

    expect(handleSuccess).toHaveBeenCalledWith(mockComparison);
    expect(handleClose).toHaveBeenCalled();
  });

  it('rejects negative cost in OutcomeEntryModal with validation message', async () => {
    const recordSpy = vi.spyOn(decisionService, 'recordOutcome');

    render(
      <OutcomeEntryModal
        isOpen={true}
        onClose={vi.fn()}
        decision={{
          decision_id: 'DEC-20261022-0001',
          shipment_id: 'SHIP000005',
        }}
      />
    );

    const costInput = screen.getByPlaceholderText('e.g. 16200.00');
    fireEvent.change(costInput, { target: { value: '-250' } });

    const submitBtn = screen.getByRole('button', { name: /Commit Actual Outcome/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText('A valid, non-negative actual cost is required.')).toBeInTheDocument();
    expect(recordSpy).not.toHaveBeenCalled();
  });

  it('switches to Closed-Loop Outcome tab in DecisionDetailModal and displays comparison', async () => {
    vi.spyOn(decisionService, 'getDecisionById').mockResolvedValue({
      decision_id: 'DEC-20261022-0001',
      shipment_id: 'SHIP000005',
      user_id: 'usr_ops_manager',
      strategy: 'AIR_FREIGHT',
      predicted_cost: 15000.0,
      predicted_delay: 1.0,
      decision_time: '2026-10-22T08:00:00Z',
      status: 'RECORDED',
    });
    vi.spyOn(decisionService, 'getOutcome').mockResolvedValue(mockComparison);

    render(
      <DecisionDetailModal
        isOpen={true}
        onClose={vi.fn()}
        decisionId="DEC-20261022-0001"
      />
    );

    // Click on Outcome tab
    const outcomeTabBtn = screen.getByRole('button', { name: /Closed-Loop Outcome Tracking/i });
    fireEvent.click(outcomeTabBtn);

    await waitFor(() => {
      expect(screen.getByText('Closed-Loop Analytics: Predicted vs Actual Outcomes')).toBeInTheDocument();
      expect(screen.getByText('$16,200.00 USD')).toBeInTheDocument();
    });
  });
});
