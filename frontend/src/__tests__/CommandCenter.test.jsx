import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import CommandCenter from '../pages/CommandCenter';
import * as optimizationService from '../services/optimizationService';
import * as decisionService from '../services/decisionService';

describe('CommandCenter Page', () => {
  const mockMetrics = {
    total_shipments: 15000,
    delayed_shipments: 4210,
    delay_rate: 0.28,
    risk_distribution: {
      HIGH: 185,
      MEDIUM: 1420,
      LOW: 13395,
    },
    average_delay_days: 3.4,
    inventory_shortage_count: 12,
  };

  const mockShipments = {
    total: 2,
    shipments: [
      {
        shipment_id: 'SHIP000005',
        product_id: 'PROD005',
        product_name: 'Precision Pressure Sensor',
        supplier_id: 'SUP002',
        supplier_name: 'Sutlej Spinning Mills',
        origin: 'Ahmedabad',
        destination: 'Delhi',
        quantity: 500,
        unit_cost: 65.0,
        shipping_cost: 3200.0,
        lead_time: 13,
        delay_days: 3,
        predicted_delay_days: 3.5,
        delay_probability: 0.85,
        risk_level: 'HIGH',
        transport_mode: 'Road',
      },
      {
        shipment_id: 'SHIP000012',
        product_id: 'PROD008',
        product_name: 'Hydraulic Valve Assembly',
        supplier_id: 'SUP001',
        supplier_name: 'Alpha Logistics Tech',
        origin: 'Mumbai',
        destination: 'Bengaluru',
        quantity: 200,
        unit_cost: 45.0,
        shipping_cost: 1500.0,
        lead_time: 18,
        delay_days: 11,
        predicted_delay_days: 11.0,
        delay_probability: 0.92,
        risk_level: 'HIGH',
        transport_mode: 'Road',
      },
    ],
  };

  const mockOptimizationResult = {
    shipment_id: 'SHIP000005',
    status: 'SUCCESS',
    prediction: {
      delay_probability: 0.85,
      predicted_delay_days: 3.5,
      risk_level: 'HIGH',
      model_version: 'v1.0',
    },
    baseline: {
      shipment_id: 'SHIP000005',
      product_id: 'PROD005',
      product_name: 'Precision Pressure Sensor',
      supplier_id: 'SUP002',
      supplier_name: 'Sutlej Spinning Mills',
      transport_mode: 'Road',
      quantity: 500,
      unit_cost: 65.0,
      shipping_cost: 3200.0,
      estimated_total_cost: 35700.0,
      predicted_delay_probability: 0.85,
      predicted_delay_days: 3.5,
      risk_level: 'HIGH',
      planned_lead_time_days: 13.0,
      total_delivery_days: 16.5,
      currency: 'USD',
    },
    options: [
      {
        option_id: 'A',
        strategy: 'AIR_FREIGHT',
        name: 'Air Freight',
        status: 'FEASIBLE',
        estimated_total_cost: 41583.04,
        additional_cost: 5883.04,
        additional_cost_percentage: 16.5,
        estimated_delivery_days: 3.5,
        schedule_impact_days: -13.0,
        delay_probability: 0.15,
        predicted_delay_days: 0.5,
        risk_level: 'LOW',
        objective_value: 41650.0,
        cost_breakdown: {
          procurement: 32500.0,
          shipping: 8500.0,
          holding: 500.0,
          delay: 83.04,
        },
        constraint_violations: [],
        assumptions: ['Modal transition to Air cargo', 'Direct airport logistics handling'],
        explanation: 'Expediting via Air Freight eliminates 13 days of transit delay and satisfies budget ceiling.',
        is_recommended: true,
      },
      {
        option_id: 'B',
        strategy: 'SECONDARY_SUPPLIER',
        name: 'Secondary Supplier (Sutlej Spinning Mills)',
        status: 'FEASIBLE',
        estimated_total_cost: 38200.0,
        additional_cost: 2500.0,
        additional_cost_percentage: 7.0,
        estimated_delivery_days: 8.0,
        schedule_impact_days: -8.5,
        delay_probability: 0.35,
        predicted_delay_days: 1.5,
        risk_level: 'MEDIUM',
        objective_value: 38550.0,
        cost_breakdown: {
          procurement: 33500.0,
          shipping: 4200.0,
          holding: 500.0,
        },
        constraint_violations: [],
        assumptions: ['Sutlej verified backup capacity available'],
        explanation: 'Secondary vendor re-allocation reduces delay to 1.5 days with lower freight surcharge.',
        is_recommended: false,
      },
      {
        option_id: 'C',
        strategy: 'DELAY_LAUNCH',
        name: 'Delay Product Launch',
        status: 'INSUFFICIENT_DATA',
        estimated_total_cost: 35700.0,
        additional_cost: 0.0,
        additional_cost_percentage: 0.0,
        estimated_delivery_days: 16.5,
        schedule_impact_days: 3.5,
        delay_probability: 0.85,
        predicted_delay_days: 3.5,
        risk_level: 'HIGH',
        objective_value: null,
        cost_breakdown: {},
        constraint_violations: [
          {
            constraint_name: 'Launch Penalty Cost',
            limit_value: 0.0,
            actual_value: 0.0,
            violation_amount: 0.0,
            message: 'Commercial penalty cost for launch delay is unconfigured.',
          },
        ],
        assumptions: ['Commercial customer penalties unconfigured in baseline'],
        explanation: 'Postponing product delivery incurs downstream SLA disruption.',
        is_recommended: false,
      },
    ],
    recommended_option_id: 'A',
    recommendation_reason: 'Option A (Air Freight) is recommended: delivers optimal balance with lowest delay risk.',
    trade_off_analysis: 'Option A incurs +$5,883.04 freight premium but recovers 13 days of supply chain delay.',
    constraint_checks: [
      {
        name: 'Maximum Budget Constraint',
        status: 'SATISFIED',
        lhs_value: 41583.04,
        rhs_value: 50000.0,
        slack: 8416.96,
        description: 'Hard budget limit ($50,000 ceiling). Candidate is within budget headroom.',
      },
      {
        name: 'Supplier Capacity Limit',
        status: 'SATISFIED',
        lhs_value: 500.0,
        rhs_value: 1000.0,
        slack: 500.0,
        description: 'Supplier monthly quota verified.',
      },
      {
        name: 'Inventory Buffer Conservation',
        status: 'SATISFIED',
        lhs_value: 100.0,
        rhs_value: 50.0,
        slack: 50.0,
        description: 'Safety reserve threshold preserved.',
      },
      {
        name: 'Delivery Window SLA',
        status: 'SATISFIED',
        lhs_value: 3.5,
        rhs_value: 20.0,
        slack: 16.5,
        description: 'Transit completes comfortably within delivery deadline.',
      },
    ],
  };

  const mockDecisionHistory = {
    total: 1,
    decisions: [
      {
        decision_id: 'DEC-20261020-0001',
        shipment_id: 'SHIP000005',
        option_id: 'A',
        strategy: 'AIR_FREIGHT',
        decision: 'Option A: Air Freight',
        decision_reason: 'Air Freight eliminates transit delay within budget ceiling.',
        status: 'RECORDED',
        estimated_total_cost: 41583.04,
        currency: 'USD',
        estimated_delivery_days: 3.5,
        external_action_status: 'NOT_EXECUTED',
        approved_by: 'Operations Manager',
        created_at: '2026-10-20T10:00:00Z',
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(optimizationService, 'getDashboardMetrics').mockResolvedValue(mockMetrics);
    vi.spyOn(optimizationService, 'getShipments').mockResolvedValue(mockShipments);
    vi.spyOn(optimizationService, 'optimizeShipment').mockResolvedValue(mockOptimizationResult);
    vi.spyOn(optimizationService, 'proposeDecision').mockResolvedValue({
      decision_id: 'DEC-OPT-TEST001',
      shipment_id: 'SHIP000005',
      option_id: 'A',
      status: 'Pending',
      message: 'Decision proposal recorded successfully.',
      recorded_at: '2026-10-19T10:00:00Z',
    });
    vi.spyOn(decisionService, 'getDecisions').mockResolvedValue({ total: 0, decisions: [] });
    vi.spyOn(decisionService, 'executeDecision').mockResolvedValue({
      decision_id: 'DEC-20261020-0002',
      shipment_id: 'SHIP000005',
      option_id: 'A',
      strategy: 'AIR_FREIGHT',
      status: 'RECORDED',
      estimated_total_cost: 41583.04,
      currency: 'USD',
      estimated_delivery_days: 3.5,
      delay_probability: 0.15,
      constraint_validation: {
        budget: 'PASS',
        inventory: 'PASS',
        supplier_capacity: 'PASS',
        delivery: 'PASS',
      },
      external_action_status: 'NOT_EXECUTED',
      message: 'Decision recorded successfully. No external booking was made.',
      recorded_at: '2026-10-20T10:05:00Z',
      idempotency_key: 'exec-SHIP000005-A-12345',
    });
  });

  it('loads telemetry and renders Command Center Header and KPI metrics', async () => {
    render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>
    );

    // Header title
    expect(screen.getByText('Command Center')).toBeInTheDocument();
    expect(screen.getByText(/Live Operations/i)).toBeInTheDocument();

    // 5 Risk Metrics KPIs
    await waitFor(() => {
      expect(screen.getByText(/Total Active Shipments/i)).toBeInTheDocument();
      expect(screen.getByText('15,000')).toBeInTheDocument();
      expect(screen.getByText(/High-Risk Shipments/i)).toBeInTheDocument();
      expect(screen.getByText('185')).toBeInTheDocument();
      expect(screen.getByText(/Predicted Delayed/i)).toBeInTheDocument();
    });
  });

  it('renders high-risk shipment banner and baseline operational summary', async () => {
    const { container } = render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Command Center')).toBeInTheDocument();
    });

    await waitFor(
      () => {
        const text = container.textContent;
        if (!text.includes('Precision Pressure Sensor') && !text.includes('High-Risk Shipment Flagged')) {
          throw new Error('Not rendered yet. Current text: ' + text.slice(0, 300));
        }
      },
      { timeout: 3000 }
    );

    expect(screen.getByText(/High-Risk Shipment Flagged/i)).toBeInTheDocument();
    expect(screen.getAllByText('SHIP000005').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Precision Pressure Sensor/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders 3 alternative recommendation cards with winning option glow and constraint status', async () => {
    render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Prescriptive Decision Alternatives/i)).toBeInTheDocument();
    });

    // 3 Cards
    expect(screen.getByText('RECOMMENDED ACTION')).toBeInTheDocument();
    expect(screen.getAllByText(/Option A/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Air Freight/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Option B/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Option C/i).length).toBeGreaterThanOrEqual(1);

    // Constraint verification gate (Day 15 audit)
    expect(screen.getByText(/Business Constraint Verification/i)).toBeInTheDocument();
    expect(screen.getByText(/Maximum Budget Constraint/i)).toBeInTheDocument();
    expect(screen.getAllByText('PASS').length).toBeGreaterThanOrEqual(4);
  });

  it('opens details modal when clicking View Details', async () => {
    render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('View Details').length).toBeGreaterThanOrEqual(1);
    });

    const viewDetailsButtons = screen.getAllByText('View Details');
    fireEvent.click(viewDetailsButtons[0]);

    // Modal opens
    await waitFor(() => {
      expect(screen.getByText(/Operational Justification/i)).toBeInTheDocument();
      expect(screen.getByText(/Itemized Cost Decomposition/i)).toBeInTheDocument();
    });

    // Close modal
    const closeBtn = screen.getByText('Close');
    fireEvent.click(closeBtn);
  });

  it('opens execute decision modal on EXECUTE DECISION, shows values, and safely executes to /api/decisions', async () => {
    render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('EXECUTE DECISION').length).toBeGreaterThanOrEqual(1);
    });

    // Click EXECUTE DECISION on the first feasible option
    const executeButtons = screen.getAllByText('EXECUTE DECISION');
    fireEvent.click(executeButtons[0].closest('button'));

    // Confirmation Modal appears with real values and governance notice
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Confirm & Execute Decision/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/Safe Operational Protocol/i)).toBeInTheDocument();
    expect(screen.getAllByText(/41,583\.04/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/3\.5 days/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/NOT_EXECUTED/i).length).toBeGreaterThanOrEqual(1);

    // Click Confirm & Execute Decision button in the modal
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Execute Decision/i });
    fireEvent.click(confirmBtn);

    // Verify decisionService.executeDecision was called with authoritative shipment & option
    await waitFor(() => {
      expect(decisionService.executeDecision).toHaveBeenCalledWith(
        expect.objectContaining({
          shipment_id: 'SHIP000005',
          option_id: 'A',
          strategy: 'AIR_FREIGHT',
          approved_by: 'Operations Manager',
        })
      );
      expect(screen.getByText(/Decision Recorded Successfully/i)).toBeInTheDocument();
    });
  });

  it('renders Decision Execution Audit Trail table with PostgreSQL records', async () => {
    vi.spyOn(decisionService, 'getDecisions').mockResolvedValue(mockDecisionHistory);

    render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Decision Execution Audit Trail/i)).toBeInTheDocument();
      expect(screen.getByText('DEC-20261020-0001')).toBeInTheDocument();
      expect(screen.getAllByText('NOT_EXECUTED').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('updates target shipment and re-optimizes when clicking optimize in shipment table', async () => {
    render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('SHIP000012')).toBeInTheDocument();
    });

    // Find table row for SHIP000012 and click its Optimize button
    const optimizeButtons = screen.getAllByText('Optimize');
    fireEvent.click(optimizeButtons[optimizeButtons.length - 1]);

    await waitFor(() => {
      expect(optimizationService.optimizeShipment).toHaveBeenCalledWith(
        expect.objectContaining({
          shipment_id: 'SHIP000012',
        })
      );
    });
  });
});
