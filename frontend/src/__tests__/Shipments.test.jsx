import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Shipments from '../pages/Shipments';
import * as api from '../services/api';

vi.mock('../services/api');

describe('Shipments Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.formatApiError.mockImplementation((err) => err?.message || 'Error occurred');
  });

  it('renders shipment list, distinguishes predictions from actual status, and shows Not Predicted badge', async () => {
    api.getSuppliers.mockResolvedValue({
      data: [{ supplier_id: 'SUP-001', supplier_name: 'Apex Global Logistics' }],
    });

    api.getShipments.mockResolvedValue({
      data: [
        {
          shipment_id: 'SHP-00001',
          supplier_id: 'SUP-001',
          supplier_name: 'Apex Global Logistics',
          product_id: 'PRD-001',
          product_name: 'Industrial Valve',
          quantity: 150,
          transport_mode: 'AIR',
          status: 'IN_TRANSIT',
          delivery_date: '2026-10-20',
          prediction_probability: 0.75,
          predicted_delay_days: 6.2,
          risk_level: 'HIGH',
        },
        {
          shipment_id: 'SHP-00002',
          supplier_id: 'SUP-001',
          supplier_name: 'Apex Global Logistics',
          product_id: 'PRD-002',
          product_name: 'Steel Coupling',
          quantity: 300,
          transport_mode: 'SEA',
          status: 'DELIVERED',
          delivery_date: '2026-10-10',
          prediction_probability: null,
          predicted_delay_days: null,
          risk_level: null,
        },
      ],
      total: 2,
      page: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter>
        <Shipments />
      </MemoryRouter>
    );

    expect(screen.getByText(/Shipment Logistics & Monitoring/i)).toBeInTheDocument();

    await waitFor(() => {
      // First shipment has HIGH risk prediction
      expect(screen.getByText('SHP-00001')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
      expect(screen.getByText('(+6.2d)')).toBeInTheDocument();

      // Second shipment has NO prediction -> clearly labeled "Not predicted"
      expect(screen.getByText('SHP-00002')).toBeInTheDocument();
      expect(screen.getByText('Not predicted')).toBeInTheDocument();
    });

    // Actual delivery outcome badge is displayed
    expect(screen.getAllByText('On-Time').length).toBeGreaterThan(0);
  });
});
