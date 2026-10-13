import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Inventory from '../pages/Inventory';
import * as api from '../services/api';

vi.mock('../services/api');

describe('Inventory Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.formatApiError.mockImplementation((err) => err?.message || 'Error occurred');
  });

  it('renders inventory items, displays stock statuses and inspects product detail modal', async () => {
    api.getInventory.mockResolvedValue({
      data: [
        {
          id: 1,
          product_id: 'PRD-001',
          product_name: 'High-Precision Bearing',
          inventory_level: 15,
          demand: 20,
          reorder_point: 50,
          safety_stock: 10,
          inventory_status: 'Low',
          inventory_date: '2026-10-01',
        },
        {
          id: 2,
          product_id: 'PRD-002',
          product_name: 'Hydraulic Cylinder',
          inventory_level: 250,
          demand: 45,
          reorder_point: 100,
          safety_stock: 30,
          inventory_status: 'Healthy',
          inventory_date: '2026-10-05',
        },
      ],
      total: 2,
      page: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter>
        <Inventory />
      </MemoryRouter>
    );

    expect(screen.getByText(/Inventory Levels & Stock Optimization/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('High-Precision Bearing')).toBeInTheDocument();
      expect(screen.getByText('Hydraulic Cylinder')).toBeInTheDocument();
      expect(screen.getByText('PRD-001')).toBeInTheDocument();
      expect(screen.getByText('PRD-002')).toBeInTheDocument();
    });

    // Verify stock status badges in table
    expect(screen.getByText('Low')).toBeInTheDocument();
    expect(screen.getByText('Healthy')).toBeInTheDocument();

    // Click Inspect to open modal
    const inspectBtn = screen.getAllByRole('button', { name: /Inspect/i })[0];
    fireEvent.click(inspectBtn);

    // Modal opens with product SKU and units
    expect(screen.getByText('SKU: PRD-001')).toBeInTheDocument();
    expect(screen.getByText('15 units')).toBeInTheDocument();
  });
});
