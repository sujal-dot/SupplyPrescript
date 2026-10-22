import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import ExecuteDecisionModal from '../components/dashboard/ExecuteDecisionModal';

describe('ExecuteDecisionModal Component', () => {
  const mockOptionFeasible = {
    option_id: 'A',
    strategy: 'AIR_FREIGHT',
    name: 'Air Freight Priority',
    status: 'FEASIBLE',
    estimated_total_cost: 41583.04,
    additional_cost: 5883.04,
    additional_cost_percentage: 16.5,
    estimated_delivery_days: 3.5,
    schedule_impact_days: -13.0,
    delay_probability: 0.15,
    risk_level: 'LOW',
    constraint_violations: [],
    assumptions: ['Direct air logistics charter verified', 'Airport ramp priority access'],
    explanation: 'Expediting via Air eliminates delay within hard budget ceiling.',
  };

  const mockOptionInfeasible = {
    option_id: 'B',
    strategy: 'SECONDARY_SUPPLIER',
    name: 'Secondary Supplier Over-Budget',
    status: 'INFEASIBLE',
    estimated_total_cost: 54200.0,
    additional_cost: 18500.0,
    additional_cost_percentage: 51.8,
    estimated_delivery_days: 7.0,
    schedule_impact_days: -9.5,
    delay_probability: 0.4,
    risk_level: 'MEDIUM',
    constraint_violations: [
      {
        constraint_name: 'Maximum Budget Constraint',
        limit_value: 50000.0,
        actual_value: 54200.0,
        violation_amount: 4200.0,
        message: 'Cost exceeds hard budget ceiling by $4,200.00.',
      },
    ],
    assumptions: [],
    explanation: 'Violates $50k maximum budget constraint.',
  };

  const mockShipment = {
    shipment_id: 'SHIP000005',
  };

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <ExecuteDecisionModal
        option={mockOptionFeasible}
        shipment={mockShipment}
        isOpen={false}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders all required details, metrics, and governance notice for feasible option', () => {
    render(
      <ExecuteDecisionModal
        option={mockOptionFeasible}
        shipment={mockShipment}
        isOpen={true}
        onClose={vi.fn()}
        onConfirmExecution={vi.fn()}
      />
    );

    // Header & Option
    expect(screen.getByRole('heading', { name: /Confirm & Execute Decision/i })).toBeInTheDocument();
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('SHIP000005')).toBeInTheDocument();

    // Financial & Delivery metrics
    expect(screen.getByText('$41,583.04')).toBeInTheDocument();
    expect(screen.getByText('3.5 days')).toBeInTheDocument();
    expect(screen.getByText(/13.0d faster/i)).toBeInTheDocument();

    // Day 15 Hard Constraints
    expect(screen.getByText(/PASS \(\$50,000 ceiling enforced\)/i)).toBeInTheDocument();

    // Safe Governance Boundary Notice
    expect(screen.getByText(/Safe Operational Protocol \(No Automated External Booking\)/i)).toBeInTheDocument();
    expect(screen.getByText('NOT_EXECUTED')).toBeInTheDocument();

    // Confirm button is enabled
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Execute Decision/i });
    expect(confirmBtn).not.toBeDisabled();
  });

  it('disables confirm button for infeasible option and highlights constraint failure', () => {
    render(
      <ExecuteDecisionModal
        option={mockOptionInfeasible}
        shipment={mockShipment}
        isOpen={true}
        onClose={vi.fn()}
        onConfirmExecution={vi.fn()}
      />
    );

    // Fail flag displayed
    expect(screen.getByText('FAIL')).toBeInTheDocument();

    // Confirm button is disabled
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Execute Decision/i });
    expect(confirmBtn).toBeDisabled();
  });

  it('calls onClose when clicking Cancel button or Close X', () => {
    const onClose = vi.fn();
    render(
      <ExecuteDecisionModal
        option={mockOptionFeasible}
        shipment={mockShipment}
        isOpen={true}
        onClose={onClose}
        onConfirmExecution={vi.fn()}
      />
    );

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);
    expect(onClose).toHaveBeenCalledTimes(1);

    const closeX = screen.getByLabelText(/Close modal/i);
    fireEvent.click(closeX);
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('submits execution payload with idempotency key, approved_by, and notes upon confirmation', () => {
    const onConfirmExecution = vi.fn();
    render(
      <ExecuteDecisionModal
        option={mockOptionFeasible}
        shipment={mockShipment}
        isOpen={true}
        onClose={vi.fn()}
        onConfirmExecution={onConfirmExecution}
      />
    );

    // Edit notes
    const notesInput = screen.getByLabelText(/Operational Notes & Context/i);
    fireEvent.change(notesInput, { target: { value: 'Approved by supply chain committee' } });

    // Click confirm
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Execute Decision/i });
    fireEvent.click(confirmBtn);

    expect(onConfirmExecution).toHaveBeenCalledTimes(1);
    expect(onConfirmExecution).toHaveBeenCalledWith(
      expect.objectContaining({
        shipment_id: 'SHIP000005',
        option_id: 'A',
        strategy: 'AIR_FREIGHT',
        approved_by: 'Operations Manager',
        notes: 'Approved by supply chain committee',
        idempotency_key: expect.stringMatching(/^exec-SHIP000005-A-\d+$/),
      })
    );
  });
});
