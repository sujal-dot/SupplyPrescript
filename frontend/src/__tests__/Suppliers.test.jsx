import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Suppliers from '../pages/Suppliers';
import * as api from '../services/api';

vi.mock('../services/api');

describe('Suppliers Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.formatApiError.mockImplementation((err) => err?.message || 'Error occurred');
  });

  it('renders supplier table and formats reliability percentage correctly', async () => {
    api.getSuppliers.mockResolvedValue({
      data: [
        {
          supplier_id: 'SUP-001',
          supplier_name: 'Apex Global Logistics',
          origin: 'Tokyo Hub',
          supplier_reliability: 0.954,
          total_shipments: 450,
          historical_avg_delay: 2.1,
          delayed_shipment_count: 24,
        },
      ],
      total: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter>
        <Suppliers />
      </MemoryRouter>
    );

    expect(screen.getByText(/Supplier Reliability & Performance/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Apex Global Logistics')).toBeInTheDocument();
      expect(screen.getByText('SUP-001')).toBeInTheDocument();
      expect(screen.getByText('Tokyo Hub')).toBeInTheDocument();
      expect(screen.getByText('95.4%')).toBeInTheDocument();
    });

    // Click profile button to inspect modal
    const profileBtn = screen.getByRole('button', { name: /Profile/i });
    fireEvent.click(profileBtn);

    // Modal opens and renders specific supplier data
    expect(screen.getByText('Origin City')).toBeInTheDocument();
    expect(screen.getByText('Historical Delay')).toBeInTheDocument();
    expect(screen.getByText('2.10 days')).toBeInTheDocument();
  });
});
