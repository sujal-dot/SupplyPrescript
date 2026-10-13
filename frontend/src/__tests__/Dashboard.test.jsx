import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';
import * as api from '../services/api';

vi.mock('../services/api');

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dashboard with real KPI metrics and high-risk shipments table', async () => {
    const mockData = {
      total_shipments: 15000,
      delayed_shipments: 3200,
      average_delay_days: 4.8,
      average_supplier_reliability: 0.942,
      risk_distribution: {
        LOW: 14,
        MEDIUM: 9,
        HIGH: 4,
      },
      delay_trends: [
        { month: '2026-01', avg_delay_days: 4.2, delayed_count: 210 },
        { month: '2026-02', avg_delay_days: 4.8, delayed_count: 245 },
      ],
      supplier_reliability_rankings: [
        { supplier_id: 'SUP-001', supplier_name: 'Apex Global Logistics', reliability_score: 0.985, total_shipments: 420 },
      ],
      high_risk_shipments: [
        {
          shipment_id: 'SHP-99881',
          supplier_id: 'SUP-002',
          supplier_name: 'Pacific Freight',
          product_id: 'PRD-102',
          product_name: 'Microcontroller A4',
          quantity: 500,
          status: 'IN_TRANSIT',
          delay_probability: 0.88,
          predicted_delay_days: 7.5,
          risk_level: 'HIGH',
        },
      ],
    };

    api.getDashboardMetrics.mockResolvedValue({
      data: mockData,
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    // Initial title check
    expect(screen.getByText(/Supply Chain Intelligence Dashboard/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('SHP-99881')).toBeInTheDocument();
    });

    // Check KPI values
    expect(screen.getByText('15,000')).toBeInTheDocument();
    expect(screen.getByText('3,200')).toBeInTheDocument();
    expect(screen.getByText('4.80')).toBeInTheDocument();
    expect(screen.getByText('94.2%')).toBeInTheDocument();
    expect(screen.getByText('Pacific Freight')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
  });

  it('renders clean empty state when no metrics exist', async () => {
    api.getDashboardMetrics.mockResolvedValue({
      data: {
        total_shipments: 0,
        delayed_shipments: 0,
        average_delay_days: null,
        average_supplier_reliability: null,
        risk_distribution: { LOW: 0, MEDIUM: 0, HIGH: 0 },
        delay_trends: [],
        supplier_reliability_rankings: [],
        high_risk_shipments: [],
      },
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/No High-Risk Shipments Flagged/i)).toBeInTheDocument();
    });
  });
});
