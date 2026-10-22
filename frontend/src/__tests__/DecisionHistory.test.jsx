import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DecisionHistory from '../components/dashboard/DecisionHistory';
import * as decisionService from '../services/decisionService';

describe('DecisionHistory Component (Day 18 Write-Back)', () => {
  const mockDecisions = [
    {
      decision_id: 'DEC-20261021-0001',
      shipment_id: 'SHIP000005',
      user_id: 'usr_ops_lead',
      recommendation: 'AIR_FREIGHT',
      option_id: 'A',
      strategy: 'AIR_FREIGHT',
      predicted_cost: 41583.04,
      predicted_delay: 0.5,
      decision_time: '2026-10-21T14:30:00Z',
      status: 'RECORDED',
      external_action_status: 'NOT_EXECUTED',
      decision_reason: 'Air freight minimizes delay to 0.5 days.',
      idempotency_key: 'idem-test-12345',
    },
    {
      decision_id: 'DEC-20261021-0002',
      shipment_id: 'SHIP000012',
      user_id: 'usr_logistics_mgr',
      recommendation: 'EXPEDITE_SUPPLIER',
      option_id: 'B',
      strategy: 'EXPEDITE_SUPPLIER',
      predicted_cost: 28400.00,
      predicted_delay: 1.2,
      decision_time: '2026-10-21T15:00:00Z',
      status: 'RECORDED',
      external_action_status: 'NOT_EXECUTED',
      decision_reason: 'Expedite supplier production.',
      idempotency_key: 'idem-test-67890',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders table headers and Day 18 write-back decision fields accurately', () => {
    render(
      <DecisionHistory
        decisions={mockDecisions}
        loading={false}
        onRefresh={vi.fn()}
        page={1}
        pageSize={10}
        total={2}
      />
    );

    // Verify headers
    expect(screen.getByText('Decision ID')).toBeInTheDocument();
    expect(screen.getByText('Shipment')).toBeInTheDocument();
    expect(screen.getByText('User')).toBeInTheDocument();
    expect(screen.getByText('Recommendation')).toBeInTheDocument();
    expect(screen.getByText('Predicted Cost')).toBeInTheDocument();
    expect(screen.getByText('Predicted Delay')).toBeInTheDocument();
    expect(screen.getByText('Internal Status')).toBeInTheDocument();
    expect(screen.getByText('External Dispatch')).toBeInTheDocument();

    // Verify row 1 fields
    expect(screen.getByText('DEC-20261021-0001')).toBeInTheDocument();
    expect(screen.getByText('SHIP000005')).toBeInTheDocument();
    expect(screen.getByText('usr_ops_lead')).toBeInTheDocument();
    expect(screen.getByText('AIR_FREIGHT')).toBeInTheDocument();
    expect(screen.getByText('$41,583.04')).toBeInTheDocument();
    expect(screen.getByText('0.5d delay')).toBeInTheDocument();

    // Verify row 2 fields
    expect(screen.getByText('DEC-20261021-0002')).toBeInTheDocument();
    expect(screen.getByText('SHIP000012')).toBeInTheDocument();
    expect(screen.getByText('usr_logistics_mgr')).toBeInTheDocument();
    expect(screen.getByText('EXPEDITE_SUPPLIER')).toBeInTheDocument();
    expect(screen.getByText('$28,400.00')).toBeInTheDocument();
    expect(screen.getByText('1.2d delay')).toBeInTheDocument();

    // Verify safety boundary status
    const notExecutedBadges = screen.getAllByText('NOT_EXECUTED');
    expect(notExecutedBadges.length).toBeGreaterThanOrEqual(2);
  });

  it('displays empty state when no decisions are recorded', () => {
    render(
      <DecisionHistory
        decisions={[]}
        loading={false}
        activeShipmentId="SHIP000005"
        showAllShipments={false}
      />
    );

    expect(screen.getByText('No Decisions Recorded Yet')).toBeInTheDocument();
    expect(screen.getByText(/No authorized execution decisions have been logged for shipment SHIP000005/i)).toBeInTheDocument();
  });

  it('handles pagination controls and triggers onPageChange callback', () => {
    const handlePageChange = vi.fn();
    const handleLimitChange = vi.fn();

    render(
      <DecisionHistory
        decisions={mockDecisions}
        loading={false}
        page={1}
        pageSize={1}
        total={2}
        onPageChange={handlePageChange}
        onPageSizeChange={handleLimitChange}
      />
    );

    expect(screen.getByText(/Showing/i)).toBeInTheDocument();
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();

    // Previous button should be disabled on page 1
    const prevBtn = screen.getByTitle('Previous Page');
    expect(prevBtn).toBeDisabled();

    // Next button should be enabled and trigger page 2
    const nextBtn = screen.getByTitle('Next Page');
    expect(nextBtn).not.toBeDisabled();
    fireEvent.click(nextBtn);
    expect(handlePageChange).toHaveBeenCalledWith(2);
  });

  it('opens DecisionDetailModal when Details button is clicked and fetches record by ID', async () => {
    const detailSpy = vi.spyOn(decisionService, 'getDecisionById').mockResolvedValue({
      ...mockDecisions[0],
      optimization_run_id: 'OPT-RUN-20261021-999',
    });

    render(
      <DecisionHistory
        decisions={mockDecisions}
        loading={false}
      />
    );

    const detailButtons = screen.getAllByRole('button', { name: /Details/i });
    fireEvent.click(detailButtons[0]);

    // Modal should open
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Decision Record Details')).toBeInTheDocument();
    expect(detailSpy).toHaveBeenCalledWith('DEC-20261021-0001');

    await waitFor(() => {
      expect(screen.getByText('OPT-RUN-20261021-999')).toBeInTheDocument();
    });

    // Close modal
    const closeBtn = screen.getByRole('button', { name: /Close Record/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
