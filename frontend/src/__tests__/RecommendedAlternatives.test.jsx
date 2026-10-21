import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import React from 'react';
import RecommendedAlternatives from '../components/prescriptions/RecommendedAlternatives';

describe('RecommendedAlternatives Component', () => {
  const mockData = {
    shipment_id: 'SHIP001',
    baseline: {
      shipment_id: 'SHIP001',
      product_id: 'PROD001',
      product_name: 'Industrial Controller Unit',
      supplier_id: 'SUP001',
      supplier_name: 'Alpha Logistics Tech',
      transport_mode: 'Road',
      quantity: 100,
      unit_cost: 50.0,
      shipping_cost: 250.0,
      estimated_total_cost: 5250.0,
      predicted_delay_probability: 0.82,
      predicted_delay_days: 8.5,
      risk_level: 'HIGH',
      planned_lead_time_days: 5.0,
      total_delivery_days: 13.5,
      currency: 'USD',
    },
    alternatives: [
      {
        option_id: 'A',
        name: 'Air Freight',
        feasibility: 'FEASIBLE',
        estimated_total_cost: 6500.0,
        additional_cost: 1250.0,
        additional_cost_percentage: 23.8,
        estimated_delivery_days: 2.5,
        schedule_impact_days: -11.0,
        delay_probability: 0.12,
        predicted_delay_days: 0.5,
        risk_level: 'LOW',
        objective_value: 6515.0,
        transport_mode: 'Air',
        supplier_id: 'SUP001',
        supplier_name: 'Alpha Logistics Tech',
        constraint_violations: [],
        assumptions: ['Air modal speedup active'],
        explanation: 'Expediting via Air Freight cuts transit time to 2.5 days.',
        is_recommended: true,
      },
      {
        option_id: 'B',
        name: 'Secondary Supplier',
        feasibility: 'FEASIBLE',
        estimated_total_cost: 5800.0,
        additional_cost: 550.0,
        additional_cost_percentage: 10.5,
        estimated_delivery_days: 7.2,
        schedule_impact_days: -6.3,
        delay_probability: 0.25,
        predicted_delay_days: 1.2,
        risk_level: 'LOW',
        objective_value: 5830.0,
        transport_mode: 'Road',
        supplier_id: 'SUP002',
        supplier_name: 'Beta Electronics Sourcing',
        constraint_violations: [],
        assumptions: ['Alternative vendor verified'],
        explanation: 'Sourcing through secondary supplier Beta Electronics Sourcing.',
        is_recommended: false,
      },
      {
        option_id: 'C',
        name: 'Delay Product Launch',
        feasibility: 'INSUFFICIENT_DATA',
        estimated_total_cost: 5250.0,
        additional_cost: 0.0,
        additional_cost_percentage: 0.0,
        estimated_delivery_days: 13.5,
        schedule_impact_days: 8.5,
        delay_probability: 0.82,
        predicted_delay_days: 8.5,
        risk_level: 'HIGH',
        objective_value: null,
        transport_mode: 'Road',
        supplier_id: 'SUP001',
        supplier_name: 'Alpha Logistics Tech',
        constraint_violations: [],
        assumptions: ['Launch commercial financial loss is unconfigured'],
        explanation: 'Postponing product launch avoids additional freight cost but commercial impact is unconfigured.',
        is_recommended: false,
      },
    ],
    recommended_option_id: 'A',
    recommendation_status: 'FEASIBLE_RECOMMENDATION',
    recommendation_reason: 'Option A (Air Freight) is recommended: optimal trade-off avoiding severe assembly line stoppage.',
    trade_off_analysis: 'Option A minimizes total delay penalty with moderate freight investment.',
    warnings: [],
    model_version: 'v1.0',
    evaluated_at: '2026-10-18T10:00:00Z',
  };

  it('renders loading state cleanly', () => {
    render(<RecommendedAlternatives loading={true} />);
    expect(screen.getByText(/Solving Prescriptive Optimization Engine/i)).toBeInTheDocument();
  });

  it('renders error state cleanly', () => {
    render(<RecommendedAlternatives error="Network timeout" />);
    expect(screen.getByText(/Prescriptive Decision Error/i)).toBeInTheDocument();
    expect(screen.getByText(/Network timeout/i)).toBeInTheDocument();
  });

  it('renders empty awaiting state cleanly', () => {
    render(<RecommendedAlternatives data={null} />);
    expect(screen.getByText(/Awaiting Shipment Selection/i)).toBeInTheDocument();
  });

  it('renders all 3 decision alternative cards and recommendation banner', () => {
    render(<RecommendedAlternatives data={mockData} />);

    // Section title
    expect(screen.getByText(/Recommended Alternative Decisions/i)).toBeInTheDocument();

    // Recommendation banner
    expect(screen.getByText(/Optimal Prescriptive Action/i)).toBeInTheDocument();
    expect(screen.getByText(/Option A \(Air Freight\) is recommended/i)).toBeInTheDocument();

    // 3 Cards and labels
    expect(screen.getAllByText(/Option A/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Air Freight/i).length).toBeGreaterThanOrEqual(1);

    expect(screen.getAllByText(/Option B/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Secondary Supplier/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Beta Electronics Sourcing/i).length).toBeGreaterThanOrEqual(1);

    expect(screen.getAllByText(/Option C/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Delay Product Launch/i).length).toBeGreaterThanOrEqual(1);

    // Trade-off Matrix
    expect(screen.getByText(/Strategic Decision Trade-off Comparison/i)).toBeInTheDocument();
  });
});
